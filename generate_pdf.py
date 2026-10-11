import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1A365D'),
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4A5568'),
        alignment=TA_CENTER
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1A365D'),
        spaceBefore=12,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#2B6CB0'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#2D3748')
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#2D3748')
    )

    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=table_cell_style,
        alignment=TA_CENTER
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1A202C')
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("Multimodal IoT Predictive Maintenance (PdM) Blueprint", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Target System:</b> Samsung WW10TP44DSX/FQ 10kg AI Ecobubble Washer &nbsp;|&nbsp; <b>Academic Context:</b> FYP Multimodal PdM", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2B6CB0'), spaceBefore=2, spaceAfter=10))

    # SECTION 1: BOM
    story.append(Paragraph("1. Complete Bill of Materials (BOM) & Purchasing List", h1_style))
    
    bom_data = [
        [
            Paragraph("<b>#</b>", table_header_style),
            Paragraph("<b>Component Name</b>", table_header_style),
            Paragraph("<b>Shop & Variant</b>", table_header_style),
            Paragraph("<b>Price</b>", table_header_style),
            Paragraph("<b>Hardware Role</b>", table_header_style)
        ],
        [
            Paragraph("1", table_cell_center),
            Paragraph("<b>NodeMCU ESP32 (30-Pin)</b>", table_cell_style),
            Paragraph("Robotedu.my<br/>ESP32 Board + USB", table_cell_style),
            Paragraph("RM 32.90", table_cell_center),
            Paragraph("240MHz dual-core MCU, Wi-Fi/BLE, hardware I2C & I2S DMA controllers.", table_cell_style)
        ],
        [
            Paragraph("2", table_cell_center),
            Paragraph("<b>ESP32 Expansion Shield</b>", table_cell_style),
            Paragraph("MakerHub MY<br/>ESP32 EXPANSION BRD (30P)", table_cell_style),
            Paragraph("RM 8.46", table_cell_center),
            Paragraph("Screw terminal interface. Clamps wires to survive 1400 RPM spin vibration.", table_cell_style)
        ],
        [
            Paragraph("3", table_cell_center),
            Paragraph("<b>MPU-6050 Accelerometer</b>", table_cell_style),
            Paragraph("ElectricA Ecom<br/>Soldered Headers", table_cell_style),
            Paragraph("RM 21.99", table_cell_center),
            Paragraph("3-axis vibration/acceleration sensing (configurable up to ±16g @ 200Hz).", table_cell_style)
        ],
        [
            Paragraph("4", table_cell_center),
            Paragraph("<b>INMP441 MEMS Microphone</b>", table_cell_style),
            Paragraph("ElectricA Ecom<br/>Soldered Headers", table_cell_style),
            Paragraph("RM 25.99", table_cell_center),
            Paragraph("Digital 24-bit I2S acoustic sensor for mechanical audio emissions.", table_cell_style)
        ],
        [
            Paragraph("5", table_cell_center),
            Paragraph("<b>Dupont Wires (40pcs)</b>", table_cell_style),
            Paragraph("MakerHub MY<br/>M-F 20cm", table_cell_style),
            Paragraph("RM 3.20", table_cell_center),
            Paragraph("Connects sensor pins (F) directly to screw shield terminals (M).", table_cell_style)
        ],
        [
            Paragraph("6", table_cell_center),
            Paragraph("<b>ABS Waterproof Project Box</b>", table_cell_style),
            Paragraph("baba168.my<br/>158x90x60mm", table_cell_style),
            Paragraph("RM 16.30", table_cell_center),
            Paragraph("IP65 weatherproof housing; flat base provides solid structural coupling.", table_cell_style)
        ],
        [
            Paragraph("7", table_cell_center),
            Paragraph("<b>PG7 Cable Glands (5pcs)</b>", table_cell_style),
            Paragraph("CASSETECH<br/>WHITE PG7", table_cell_style),
            Paragraph("RM 2.50", table_cell_center),
            Paragraph("Watertight rubber compression seal for USB cable entry.", table_cell_style)
        ],
        [
            Paragraph("8", table_cell_center),
            Paragraph("<b>3M Original VHB Tape</b>", table_cell_style),
            Paragraph("3M shop<br/>2.5cm x 3m (0.8mm)", table_cell_style),
            Paragraph("RM 14.61", table_cell_center),
            Paragraph("High-stiffness acrylic bond. Transmits vibration without damping signals.", table_cell_style)
        ],
        [
            Paragraph("", table_cell_center),
            Paragraph("<b>ESTIMATED TOTAL</b>", table_cell_style),
            Paragraph("All Components Complete", table_cell_style),
            Paragraph("<b>~RM 125.95</b>", table_cell_center),
            Paragraph("Ready-to-deploy multimodal hardware testbed.", table_cell_style)
        ]
    ]

    bom_table = Table(bom_data, colWidths=[24, 130, 110, 60, 216])
    bom_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A365D')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F7FAFC')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#F7FAFC')),
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#F7FAFC')),
        ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#F7FAFC')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),
    ]))
    story.append(bom_table)
    story.append(Spacer(1, 12))

    # SECTION 2: WIRING DIAGRAM
    story.append(Paragraph("2. Pin-by-Pin Wiring Diagram & Pinout Table", h1_style))
    story.append(Paragraph("Both sensors are powered via the <b>3.3V (3V3)</b> rail. The MPU-6050 communicates via <b>I2C</b>, while the INMP441 streams audio over <b>I2S DMA</b>.", body_style))
    story.append(Spacer(1, 6))

    wiring_data = [
        [
            Paragraph("<b>Sensor</b>", table_header_style),
            Paragraph("<b>Sensor Pin</b>", table_header_style),
            Paragraph("<b>ESP32 Pin</b>", table_header_style),
            Paragraph("<b>Protocol / Signal</b>", table_header_style),
            Paragraph("<b>Wire Color</b>", table_header_style),
            Paragraph("<b>Functional Description</b>", table_header_style)
        ],
        # MPU-6050
        [Paragraph("MPU-6050", table_cell_center), Paragraph("<b>VCC</b>", table_cell_style), Paragraph("<b>3V3</b>", table_cell_style), Paragraph("Power (3.3V)", table_cell_style), Paragraph("Red", table_cell_style), Paragraph("Clean regulated logic power supply", table_cell_style)],
        [Paragraph("MPU-6050", table_cell_center), Paragraph("<b>GND</b>", table_cell_style), Paragraph("<b>GND</b>", table_cell_style), Paragraph("Ground (0V)", table_cell_style), Paragraph("Black", table_cell_style), Paragraph("Common ground return path", table_cell_style)],
        [Paragraph("MPU-6050", table_cell_center), Paragraph("<b>SCL</b>", table_cell_style), Paragraph("<b>GPIO 22</b>", table_cell_style), Paragraph("I2C Clock", table_cell_style), Paragraph("Yellow", table_cell_style), Paragraph("I2C Serial Clock synchronization line", table_cell_style)],
        [Paragraph("MPU-6050", table_cell_center), Paragraph("<b>SDA</b>", table_cell_style), Paragraph("<b>GPIO 21</b>", table_cell_style), Paragraph("I2C Data", table_cell_style), Paragraph("Green", table_cell_style), Paragraph("Bi-directional I2C telemetry data line", table_cell_style)],
        [Paragraph("MPU-6050", table_cell_center), Paragraph("<b>AD0</b>", table_cell_style), Paragraph("<b>GND</b>", table_cell_style), Paragraph("Address Pin", table_cell_style), Paragraph("Blue", table_cell_style), Paragraph("Ties address bit to lock I2C address to 0x68", table_cell_style)],
        # INMP441
        [Paragraph("INMP441", table_cell_center), Paragraph("<b>VDD</b>", table_cell_style), Paragraph("<b>3V3</b>", table_cell_style), Paragraph("Power (3.3V)", table_cell_style), Paragraph("Red", table_cell_style), Paragraph("Digital MEMS microphone power supply", table_cell_style)],
        [Paragraph("INMP441", table_cell_center), Paragraph("<b>GND</b>", table_cell_style), Paragraph("<b>GND</b>", table_cell_style), Paragraph("Ground (0V)", table_cell_style), Paragraph("Black", table_cell_style), Paragraph("Common audio ground", table_cell_style)],
        [Paragraph("INMP441", table_cell_center), Paragraph("<b>SCK</b>", table_cell_style), Paragraph("<b>GPIO 33</b>", table_cell_style), Paragraph("I2S BCLK", table_cell_style), Paragraph("Orange", table_cell_style), Paragraph("Bit Clock for continuous serial audio bits", table_cell_style)],
        [Paragraph("INMP441", table_cell_center), Paragraph("<b>WS</b>", table_cell_style), Paragraph("<b>GPIO 25</b>", table_cell_style), Paragraph("I2S LRCLK", table_cell_style), Paragraph("White", table_cell_style), Paragraph("Word Select / Left-Right Frame clock", table_cell_style)],
        [Paragraph("INMP441", table_cell_center), Paragraph("<b>SD</b>", table_cell_style), Paragraph("<b>GPIO 32</b>", table_cell_style), Paragraph("I2S DIN", table_cell_style), Paragraph("Gray", table_cell_style), Paragraph("Serial Data input stream into ESP32 DMA", table_cell_style)],
        [Paragraph("INMP441", table_cell_center), Paragraph("<b>L/R</b>", table_cell_style), Paragraph("<b>GND</b>", table_cell_style), Paragraph("Channel Sel", table_cell_style), Paragraph("Purple", table_cell_style), Paragraph("Pull to GND to stream mono on Left channel", table_cell_style)]
    ]

    wiring_table = Table(wiring_data, colWidths=[55, 55, 60, 75, 55, 240])
    wiring_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('BACKGROUND', (0, 1), (-1, 5), colors.HexColor('#F7FAFC')),
        ('BACKGROUND', (0, 6), (-1, -1), colors.white),
    ]))
    story.append(wiring_table)
    story.append(Spacer(1, 14))

    # SECTION 3: STEP-BY-STEP CHECKLIST
    story.append(Paragraph("3. Step-by-Step Checklist: What to Do Once Everything Arrives", h1_style))

    story.append(Paragraph("<b>Phase 1: Benchtop Testing & Smoke Verification (30 Minutes)</b>", h2_style))
    story.append(Paragraph("• <b>Seat the ESP32:</b> Align the 30-pin board into the MakerHub expansion shield. Inspect all pins to ensure none are bent.", bullet_style))
    story.append(Paragraph("• <b>Plug in USB:</b> Connect to PC and verify COM port detection under Device Manager (CP2102 driver).", bullet_style))
    story.append(Paragraph("• <b>I2C Verification:</b> Wire MPU-6050 (VCC, GND, GPIO 21, GPIO 22, AD0->GND). Run an I2C Scanner sketch in Arduino IDE. Verify device acknowledges at address <code>0x68</code>.", bullet_style))
    story.append(Paragraph("• <b>I2S Acoustic Verification:</b> Wire INMP441 (GPIO 33, 25, 32). Flash a test script and view live audio waveforms in the Arduino Serial Plotter.", bullet_style))

    story.append(Paragraph("<b>Phase 2: Enclosure Preparation & Mounting (45 Minutes)</b>", h2_style))
    story.append(Paragraph("• <b>Cable Gland Hole:</b> Drill a 12mm hole on the side/bottom wall of the ABS box. Fit the PG7 gland with its rubber O-ring.", bullet_style))
    story.append(Paragraph("• <b>Acoustic Port:</b> Drill a 1.5mm - 2mm pinhole in the lower part of a <b>side wall</b> (not the bottom face, which the VHB tape covers), lined up with the INMP441 sound port. See Section 4.", bullet_style))
    story.append(Paragraph("• <b>Internal Sensor Anchor:</b> Tape the MPU-6050 flat against the interior base of the ABS box with a small piece of VHB tape. (Never allow the accelerometer to float loose on jumper wires).", bullet_style))
    story.append(Paragraph("• <b>Chassis Bonding:</b> Clean the top-rear metal casing of your Samsung washer with alcohol. Stick the enclosure down with 3M VHB tape and apply firm pressure for 30 seconds.", bullet_style))

    story.append(Paragraph("<b>Phase 3: Machine Baselines & Synthetic Fault Experiments</b>", h2_style))
    story.append(Paragraph("• <b>Healthy Baseline Run:</b> Record telemetry during a standard Daily/Cotton cycle (3-4kg mixed clothing) at 1400 RPM.", bullet_style))
    story.append(Paragraph("• <b>Synthetic Fault 1 (Unbalance):</b> Run a spin cycle with 1 single heavy wet bath towel to test the 1X RPM unbalance anomaly detector.", bullet_style))
    story.append(Paragraph("• <b>Synthetic Fault 2 (Loose Foot):</b> Loosen one front rubber leveling foot by 2 turns to test rocking and structural harmonic anomalies.", bullet_style))

    # SECTION 4: DRILLING GUIDE
    story.append(Spacer(1, 10))
    story.append(Paragraph("4. Enclosure Drilling Guide: 12 mm Gland Hole & Microphone Port", h1_style))

    story.append(Paragraph("Why 12 mm?", h2_style))
    story.append(Paragraph("The hole holds the <b>PG7 cable gland</b>, which lets the USB power cable enter the box without letting water in. PG7 has an outer thread diameter of about 12.5 mm, so drill <b>12 mm</b> and open it very slightly with a round file or the side of the bit. The gland should thread in with light resistance and the locknut should sit flat against the wall. If the hole is too loose, the gasket cannot seal.", body_style))

    story.append(Paragraph("How to drill ABS plastic", h2_style))
    story.append(Paragraph("• <b>1. Empty the box.</b> Take the electronics out so plastic shavings do not land on them.", bullet_style))
    story.append(Paragraph("• <b>2. Mark and dent.</b> Mark the spot with a pencil and make a small dent with a nail or centre punch so the bit does not wander.", bullet_style))
    story.append(Paragraph("• <b>3. Step up gradually.</b> Drill a 3 mm pilot hole, then 6 mm, then 12 mm. A <b>step (cone) drill bit</b> is better if available: it cuts a clean round hole in thin plastic in one pass.", bullet_style))
    story.append(Paragraph("• <b>4. Low speed, light pressure.</b> Clamp or firmly hold the box. ABS is soft but cracks or grabs if you rush a large bit.", bullet_style))
    story.append(Paragraph("• <b>5. Deburr.</b> Clean the hole edge with a knife or sandpaper so the gasket sits flat.", bullet_style))

    story.append(Paragraph("Where to put the hole", h2_style))
    story.append(Paragraph("• Use a <b>side or bottom wall that will not face the washer</b>, since the box sits flush on the chassis.", bullet_style))
    story.append(Paragraph("• Let the cable leave in a small downward <b>drip loop</b> so rain drips off the bottom of the loop instead of running along the cable into the gland.", bullet_style))
    story.append(Spacer(1, 8))

    def callout(title, text):
        t = Table([[Paragraph("<b>" + title + "</b><br/>" + text, table_cell_style)]], colWidths=[540])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFAF0')),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#DD6B20')),
            ('LINEBEFORE', (0, 0), (0, -1), 3, colors.HexColor('#DD6B20')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return KeepTogether([t, Spacer(1, 8)])

    story.append(callout(
        "CHECK 1: Will the USB plug fit through the gland?",
        "A PG7 gland grips cables of roughly 3 to 6.5 mm, but the rubber insert opening can be tight for a plug. Micro-USB usually passes, but USB-C is wider and may not. <b>Test your connector through the gland before drilling.</b> If it will not pass, feed the bare cable through and connect inside the box, or use a cable with a smaller plug."
    ))
    story.append(callout(
        "CHECK 2: Microphone pinhole position",
        "The VHB tape covers the entire bottom face of the box, which would block a hole drilled there. Drill the 1.5 to 2 mm pinhole in the <b>lower part of a side wall</b>, lined up with the INMP441 sound port, facing sideways or down so rain cannot run in. Check where the port sits on your board before drilling."
    ))

    # SECTION 5: FIRMWARE NOTES
    story.append(Paragraph("5. Firmware Notes Before Real Data Collection", h1_style))
    story.append(Paragraph("• <b>1. Raise the MPU-6050 filter bandwidth.</b> <font name='Courier'>02_multimodal_telemetry_test.ino</font> sets <font name='Courier'>MPU6050_BAND_44_HZ</font>. At 1400 RPM the spin fundamental is about 23 Hz and the 2x harmonic is about 47 Hz, which a 44 Hz filter attenuates. Change it to <font name='Courier'>MPU6050_BAND_94_HZ</font> or <font name='Courier'>MPU6050_BAND_184_HZ</font>.", bullet_style))
    story.append(Paragraph("• <b>2. Use a fixed sample rate.</b> The loop blocks on <font name='Courier'>i2s_read</font> and also uses <font name='Courier'>delay(10)</font>, so the rate is irregular and likely below 100 Hz. Fine for bench tests, but for FFT features use a timed sampling loop or a separate audio task so the rate is a stable 200 Hz.", bullet_style))

    doc.build(story)
    print("PDF successfully generated!")

if __name__ == '__main__':
    build_pdf("G:/My Drive/PdM SideProject/hardware_bom_and_setup_guide.pdf")
