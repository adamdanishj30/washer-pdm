/**
 * test_csv_parser_parity.js
 * Verifies parity of the client-side parseCsvData() implementation extracted from historical.html
 * against Python load_csv() for firmware-07 (V3 schema) files, and against the previous legacy
 * implementation from git HEAD for legacy firmware 05/06 files.
 *
 * Run: node firmware/tests/test_csv_parser_parity.js
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');

// 1. Extract new parseCsvData from historical.html
const historicalHtml = fs.readFileSync(path.join(ROOT, 'historical.html'), 'utf8');
const match = historicalHtml.match(/function parseCsvData\(text\)[\s\S]*?\n    \}/);
if (!match) {
  console.error('[FAIL] Could not extract parseCsvData from historical.html');
  process.exit(1);
}

// Evaluate parseCsvData in current context
const newParseCsvData = new Function('text', match[0] + '\nreturn parseCsvData(text);');

// 2. Extract old parseCsvData from git show HEAD:historical.html
let oldParseCsvData;
try {
  const oldHtml = execSync('git show HEAD:historical.html', { cwd: ROOT, encoding: 'utf8' });
  const oldMatch = oldHtml.match(/function parseCsvData\(text\)[\s\S]*?\n    \}/);
  if (!oldMatch) {
    throw new Error('Could not find old parseCsvData in HEAD:historical.html');
  }
  oldParseCsvData = new Function('text', oldMatch[0] + '\nreturn parseCsvData(text);');
} catch (err) {
  console.error('[FAIL] Error extracting old parseCsvData from git HEAD:', err.message);
  process.exit(1);
}

// =============================================================================
// STEP 7: Firmware-07 parity with Python load_csv()
// =============================================================================
const fw07Files = [
  'data/real_sessions/wash_cycle_2026-10-20_0744.csv',
  'data/real_sessions/wash_cycle_2026-10-19_0911.csv'
];

for (const relPath of fw07Files) {
  const fullPath = path.join(ROOT, relPath);
  if (!fs.existsSync(fullPath)) {
    console.error(`[FAIL] File not found: ${relPath}`);
    process.exit(1);
  }

  const csvText = fs.readFileSync(fullPath, 'utf8');
  const jsRecords = newParseCsvData(csvText);

  // Run python load_csv on the same file
  const pyCmd = `py -c "import json, build_clean_dashboard; print(json.dumps(build_clean_dashboard.load_csv(r'${fullPath}')))"`;
  let pyJson;
  try {
    pyJson = execSync(pyCmd, { cwd: ROOT, encoding: 'utf8' });
  } catch (err) {
    console.error(`[FAIL] Python execution failed for ${relPath}:`, err.message);
    process.exit(1);
  }
  const pyRecords = JSON.parse(pyJson.trim());

  if (jsRecords.length !== pyRecords.length) {
    console.error(`[FAIL] Row count mismatch on ${relPath}: JS ${jsRecords.length} vs Py ${pyRecords.length}`);
    process.exit(1);
  }

  for (let r = 0; r < jsRecords.length; r++) {
    const jsRec = jsRecords[r];
    const pyRec = pyRecords[r];

    if (jsRec.length !== 12) {
      console.error(`[FAIL] Row ${r} on ${relPath} does not have length 12: len=${jsRec.length}`);
      process.exit(1);
    }
    if (pyRec.length !== 12) {
      console.error(`[FAIL] Python Row ${r} on ${relPath} does not have length 12: len=${pyRec.length}`);
      process.exit(1);
    }
    if (jsRec[7] !== 'w') {
      console.error(`[FAIL] Row ${r} on ${relPath} index 7 is '${jsRec[7]}', expected 'w'`);
      process.exit(1);
    }

    for (let c = 0; c < 12; c++) {
      if (c === 7) continue; // string 'w'
      const jVal = jsRec[c];
      const pVal = pyRec[c];

      const jNull = (jVal === null || jVal === undefined);
      const pNull = (pVal === null || pVal === undefined);
      if (jNull !== pNull) {
        console.error(`[FAIL] Null mismatch on ${relPath} row ${r} col ${c}: JS ${jVal} vs Py ${pVal}`);
        process.exit(1);
      }
      if (!jNull) {
        const diff = Math.abs(jVal - pVal);
        if (diff > 1e-4) {
          console.error(`[FAIL] Value mismatch on ${relPath} row ${r} col ${c}: JS ${jVal} vs Py ${pVal} (diff ${diff} > 1e-4)`);
          process.exit(1);
        }
      }
    }
  }

  console.log(`[PASS] Firmware-07 parity: ${relPath} (${jsRecords.length} rows, 12 columns, max diff <= 1e-4, nulls aligned)`);
}

// =============================================================================
// STEP 8: Legacy parity with OLD parseCsvData()
// =============================================================================
const legacyFiles = [
  'data/real_sessions/wash_cycle_2026-10-17_0835.csv',
  'data/real_sessions/wash_cycle_2026-10-12_1019.csv'
];

for (const relPath of legacyFiles) {
  const fullPath = path.join(ROOT, relPath);
  if (!fs.existsSync(fullPath)) {
    console.error(`[FAIL] File not found: ${relPath}`);
    process.exit(1);
  }

  const csvText = fs.readFileSync(fullPath, 'utf8');
  const oldRecs = oldParseCsvData(csvText);
  const newRecs = newParseCsvData(csvText);

  const oldJson = JSON.stringify(oldRecs);
  const newJson = JSON.stringify(newRecs);

  if (oldJson !== newJson) {
    console.error(`[FAIL] Legacy parity failed on ${relPath}: outputs not byte-identical!`);
    console.error('Old length:', oldRecs.length, 'New length:', newRecs.length);
    process.exit(1);
  }

  console.log(`[PASS] Legacy parity: ${relPath} (${newRecs.length} rows, byte-identical JSON)`);
}

console.log('[ALL PASS] test_csv_parser_parity: Both firmware-07 and legacy CSV parsing verified.');
