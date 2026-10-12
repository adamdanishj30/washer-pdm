/**
 * =========================================================================
 * Washer PdM: Cloud-to-Drive Autonomous Telemetry Sync (Google Apps Script)
 * =========================================================================
 * Runs 100% inside Google Cloud (No computer or laptop needed!).
 * 
 * Monitored in real-time every 1 minute:
 * As soon as the ESP32 finishes transmitting and is detected as OFFLINE
 * (after 10 to 60 seconds of inactivity), this script automatically:
 *   1. Fetches all recorded batches for the wash session from Firebase RTDB.
 *   2. Converts the sensor telemetry into a standardized CSV dataset:
 *      (timestamp_ms, accel_x, accel_y, accel_z, audio_rms).
 *   3. Saves the CSV file directly into your Google Drive folder:
 *      'PdM SideProject/data/wash_cycle_YYYY-MM-DD_HHMM.csv'.
 *   4. Sends an optional email notification to your Gmail with a direct Drive link!
 *   5. Marks the session archived so it never duplicates.
 * 
 * -------------------------------------------------------------------------
 * QUICK SETUP (Takes ~2 minutes):
 * 1. Open https://script.google.com/ in your browser.
 * 2. Click "+ New project".
 * 3. Delete any default code, paste this entire file, and click Save (Ctrl+S).
 * 4. In the function dropdown at the top, select "installTrigger" and click "Run".
 * 5. Grant permissions when prompted by Google.
 * 6. DONE! Google Apps Script will now monitor Firebase 24/7 in the cloud.
 * =========================================================================
 */

const FIREBASE_HOST = "https://pdm-anomaly-detection-default-rtdb.asia-southeast1.firebasedatabase.app";
const FIREBASE_AUTH = "18mHDNCCisVdpFjUHbPnOASYWbZylX1QQ5sCx61V";
const DRIVE_FOLDER_NAME = "PdM SideProject"; // Target Google Drive folder
const SEND_EMAIL_NOTIFICATION = true;       // Set to false if you don't want emails

/**
 * Main scheduled trigger function (Runs every 1 minute via Time-driven Trigger)
 */
function checkRigAndSyncToDrive() {
  const props = PropertiesService.getScriptProperties();
  const nowMs = Date.now();
  
  // 1. Fetch current live status from Firebase
  let live = null;
  try {
    const liveRes = UrlFetchApp.fetch(`${FIREBASE_HOST}/live.json`, { muteHttpExceptions: true });
    if (liveRes.getResponseCode() === 200) {
      live = JSON.parse(liveRes.getContentText());
    }
  } catch (e) {
    Logger.log("Firebase connection error: " + e);
    return;
  }
  
  if (!live) return;
  
  const curCnt = live.cnt || 0;
  const curUptime = live.uptime || 0;
  const curSession = live.session || "wash_unknown";
  
  // Retrieve previous state
  const prevCnt = parseInt(props.getProperty("last_cnt") || "-1", 10);
  const prevUptime = parseInt(props.getProperty("last_uptime") || "-1", 10);
  const wasOnline = props.getProperty("is_online") === "true";
  const lastActiveSession = props.getProperty("active_session") || curSession;
  const lastPacketTime = parseInt(props.getProperty("last_packet_time") || "0", 10);
  
  // Check if packets have advanced
  const isAdvancing = (prevCnt !== -1 && curCnt !== prevCnt) || 
                      (prevUptime !== -1 && curUptime !== prevUptime);
  
  if (isAdvancing) {
    // ESP32 is actively streaming
    props.setProperty("last_cnt", curCnt.toString());
    props.setProperty("last_uptime", curUptime.toString());
    props.setProperty("is_online", "true");
    props.setProperty("active_session", curSession);
    props.setProperty("last_packet_time", nowMs.toString());
    Logger.log(`[ONLINE] ESP32 streaming actively. Session: ${curSession}, Cnt: ${curCnt}`);
    return;
  }
  
  // Telemetry did NOT advance: check duration of inactivity
  const inactiveMs = nowMs - lastPacketTime;
  const OFFLINE_THRESHOLD_MS = 25 * 1000; // 25 seconds of inactivity = OFFLINE
  
  if (wasOnline && inactiveMs >= OFFLINE_THRESHOLD_MS) {
    // RIG JUST WENT OFFLINE! Trigger automatic session export to Google Drive!
    Logger.log(`[OFFLINE DETECTED] Rig inactive for ${Math.round(inactiveMs / 1000)}s! Archiving session: ${lastActiveSession}`);
    props.setProperty("is_online", "false");
    
    archiveSessionToDrive(lastActiveSession);
  }
}

/**
 * Downloads a session from Firebase, formats CSV, and saves directly to Google Drive.
 */
function archiveSessionToDrive(sessionId) {
  const props = PropertiesService.getScriptProperties();
  const archivedKey = `archived_${sessionId}`;
  
  if (props.getProperty(archivedKey) === "true") {
    Logger.log(`Session ${sessionId} already archived. Skipping duplicate.`);
    return;
  }
  
  Logger.log(`Fetching session '${sessionId}' data from Firebase...`);
  let sessionData = null;
  try {
    const res = UrlFetchApp.fetch(`${FIREBASE_HOST}/sessions/${sessionId}.json`, { muteHttpExceptions: true });
    if (res.getResponseCode() === 200) {
      sessionData = JSON.parse(res.getContentText());
    }
  } catch (e) {
    Logger.log(`Error fetching session data: ${e}`);
    return;
  }
  
  if (!sessionData) {
    Logger.log(`No data found for session: ${sessionId}`);
    return;
  }
  
  // Extract and sort batch records
  const rows = [];
  if (Array.isArray(sessionData)) {
    sessionData.forEach(item => {
      if (item && typeof item === "object" && item.ax !== undefined) {
        rows.push(item);
      }
    });
  } else if (typeof sessionData === "object") {
    Object.keys(sessionData)
      .sort((a, b) => parseInt(a, 10) - parseInt(b, 10))
      .forEach(k => {
        const item = sessionData[k];
        if (item && typeof item === "object" && item.ax !== undefined) {
          rows.push(item);
        }
      });
  }
  
  if (rows.length < 3) {
    Logger.log(`Session ${sessionId} has insufficient data (${rows.length} points).`);
    return;
  }
  
  // Determine standard file name: wash_cycle_YYYY-MM-DD_HHMM.csv
  const now = new Date();
  const dateStr = Utilities.formatDate(now, "GMT+8", "yyyy-MM-dd_HHmm");
  const fileName = `wash_cycle_${dateStr}.csv`;
  
  // Build CSV content
  let csvContent = "timestamp_ms,accel_x,accel_y,accel_z,audio_rms\n";
  rows.forEach(r => {
    const t = r.t || 0;
    const ax = Number(r.ax || 0).toFixed(2);
    const ay = Number(r.ay || 0).toFixed(2);
    const az = Number(r.az || 0).toFixed(2);
    const rms = Number(r.rms || 0).toFixed(1);
    csvContent += `${t},${ax},${ay},${az},${rms}\n`;
  });
  
  // Locate or create target folder in Google Drive
  const targetFolder = getOrCreateDriveFolder();
  const file = targetFolder.createFile(fileName, csvContent, MimeType.CSV);
  
  Logger.log(`[SAVED TO DRIVE] File created: ${file.getName()} (${rows.length} records)`);
  Logger.log(`File Drive URL: ${file.getUrl()}`);
  
  // Mark archived in ScriptProperties and Firebase
  props.setProperty(archivedKey, "true");
  try {
    UrlFetchApp.fetch(`${FIREBASE_HOST}/archived_sessions/${sessionId}.json?auth=${FIREBASE_AUTH}`, {
      method: "put",
      contentType: "application/json",
      payload: JSON.stringify({
        archived_at: now.toISOString(),
        filename: fileName,
        points: rows.length,
        drive_url: file.getUrl()
      }),
      muteHttpExceptions: true
    });
  } catch (e) {}
  
  // Optional Email Notification
  if (SEND_EMAIL_NOTIFICATION) {
    try {
      const userEmail = Session.getActiveUser().getEmail();
      if (userEmail) {
        const subject = `🧺 Wash Cycle Finished: ${fileName} is Ready in Google Drive`;
        const body = `Hi Adam,\n\nYour Samsung washing machine cycle has completed and the ESP32 rig has powered down.\n\n` +
                     `Telemetry Summary:\n` +
                     `• Session ID: ${sessionId}\n` +
                     `• Total Data Points: ${rows.length}\n` +
                     `• Filename: ${fileName}\n` +
                     `• Google Drive Link: ${file.getUrl()}\n\n` +
                     `The CSV has been stored directly in your Google Drive and is ready for predictive maintenance analytics.\n\n` +
                     `Best,\nWasher PdM Cloud Automation`;
        MailApp.sendEmail(userEmail, subject, body);
        Logger.log(`Notification email sent to: ${userEmail}`);
      }
    } catch (e) {
      Logger.log(`Could not send email: ${e}`);
    }
  }
}

/**
 * Helper to get or create target Google Drive folder: 'PdM SideProject/data'
 */
function getOrCreateDriveFolder() {
  let rootFolder;
  const parentFolders = DriveApp.getFoldersByName(DRIVE_FOLDER_NAME);
  if (parentFolders.hasNext()) {
    rootFolder = parentFolders.next();
  } else {
    rootFolder = DriveApp.createFolder(DRIVE_FOLDER_NAME);
  }
  
  const subFolders = rootFolder.getFoldersByName("data");
  if (subFolders.hasNext()) {
    return subFolders.next();
  }
  return rootFolder.createFolder("data");
}

/**
 * Installs the automatic 1-minute time trigger with a single click
 */
function installTrigger() {
  // Remove any duplicate existing triggers
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(t => {
    if (t.getHandlerFunction() === "checkRigAndSyncToDrive") {
      ScriptApp.deleteTrigger(t);
    }
  });
  
  // Create 1-minute recurring trigger
  ScriptApp.newTrigger("checkRigAndSyncToDrive")
    .timeBased()
    .everyMinutes(1)
    .create();
    
  Logger.log("[SUCCESS] 1-minute background trigger installed successfully!");
  Logger.log("Google Apps Script is now actively monitoring Firebase 24/7 in the cloud.");
}

/**
 * Manual test function to sync all existing sessions immediately
 */
function manualSyncAllSessions() {
  try {
    const res = UrlFetchApp.fetch(`${FIREBASE_HOST}/sessions.json?shallow=true`, { muteHttpExceptions: true });
    if (res.getResponseCode() === 200) {
      const sessions = JSON.parse(res.getContentText());
      if (sessions) {
        Object.keys(sessions).forEach(s_id => {
          Logger.log(`Processing session: ${s_id}`);
          archiveSessionToDrive(s_id);
        });
      }
    }
  } catch (e) {
    Logger.log("Error during manual sync: " + e);
  }
}
