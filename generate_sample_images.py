"""
generate_sample_images.py

Creates two demo folders, each with 5 filename-matched PNG images that look
like terminal/screen captures of COBOL source + run output:

    sample_data/actual_output/PROGRAM1.png ... PROGRAM5.png
    sample_data/expected_output/PROGRAM1.png ... PROGRAM5.png

Each pair shares the same filename but has a small, deliberate difference
(a changed literal, a flipped condition, a typo, etc.) so the FastAPI
backend has something real to detect. This is only test/demo data -- in
real use the user uploads their own COBOL screenshots.
"""

from PIL import Image, ImageDraw, ImageFont
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ACTUAL_DIR = os.path.join(BASE, "sample_data", "actual_output")
EXPECTED_DIR = os.path.join(BASE, "sample_data", "expected_output")

os.makedirs(ACTUAL_DIR, exist_ok=True)
os.makedirs(EXPECTED_DIR, exist_ok=True)

WIDTH, HEIGHT = 760, 520
BG = (12, 12, 30)
FG = (80, 255, 120)
HEADER_BG = (30, 30, 60)


def get_font(size=16):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


FONT = get_font(15)
FONT_BOLD = get_font(16)


def render_screen(filename, title, lines):
    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, WIDTH, 34], fill=HEADER_BG)
    draw.text((14, 8), title, font=FONT_BOLD, fill=(255, 255, 255))
    y = 50
    for line in lines:
        draw.text((18, y), line, font=FONT, fill=FG)
        y += 22
    return img


# Five COBOL "programs". Each entry defines the shared source lines plus
# one line that differs between the actual run and the expected run.
PROGRAMS = [
    {
        "name": "PROGRAM1",
        "title": "PROGRAM1.cbl - run output",
        "common_top": [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. PROGRAM1.",
            "DATA DIVISION.",
            "WORKING-STORAGE SECTION.",
            "01 WS-PRICE     PIC 9(4)V99 VALUE 100.00.",
            "01 WS-QTY       PIC 9(3)    VALUE 5.",
            "01 WS-TOTAL     PIC 9(6)V99.",
            "PROCEDURE DIVISION.",
            "    MULTIPLY WS-PRICE BY WS-QTY GIVING WS-TOTAL.",
            "    DISPLAY 'TOTAL AMOUNT: ' WS-TOTAL.",
            "",
            "--- OUTPUT ---",
        ],
        "actual_line": "TOTAL AMOUNT: 000600.00",
        "expected_line": "TOTAL AMOUNT: 000500.00",
    },
    {
        "name": "PROGRAM2",
        "title": "PROGRAM2.cbl - run output",
        "common_top": [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. PROGRAM2.",
            "DATA DIVISION.",
            "WORKING-STORAGE SECTION.",
            "01 WS-AGE       PIC 9(3) VALUE 17.",
            "01 WS-STATUS    PIC X(10).",
            "PROCEDURE DIVISION.",
            "    IF WS-AGE >= 18",
            "        MOVE 'ADULT' TO WS-STATUS",
            "    ELSE",
            "        MOVE 'MINOR' TO WS-STATUS",
            "    END-IF.",
            "    DISPLAY 'STATUS: ' WS-STATUS.",
            "",
            "--- OUTPUT ---",
        ],
        "actual_line": "STATUS: ADULT",
        "expected_line": "STATUS: MINOR",
    },
    {
        "name": "PROGRAM3",
        "title": "PROGRAM3.cbl - run output",
        "common_top": [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. PROGRAM3.",
            "DATA DIVISION.",
            "WORKING-STORAGE SECTION.",
            "01 WS-A     PIC 9(3) VALUE 10.",
            "01 WS-B     PIC 9(3) VALUE 25.",
            "01 WS-SUM   PIC 9(4).",
            "PROCEDURE DIVISION.",
            "    ADD WS-A TO WS-B GIVING WS-SUM.",
            "    DISPLAY 'SUM = ' WS-SUM.",
            "",
            "--- OUTPUT ---",
        ],
        "actual_line": "SUM = 0036",
        "expected_line": "SUM = 0035",
    },
    {
        "name": "PROGRAM4",
        "title": "PROGRAM4.cbl - run output",
        "common_top": [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. PROGRAM4.",
            "DATA DIVISION.",
            "WORKING-STORAGE SECTION.",
            "01 WS-NAME   PIC X(15) VALUE 'JOHN SMITH'.",
            "PROCEDURE DIVISION.",
            "    DISPLAY 'HELLO, ' WS-NAME.",
            "",
            "--- OUTPUT ---",
        ],
        "actual_line": "HELLO, JOHN SMITH",
        "expected_line": "HELLO, JOHN SMYTH",
    },
    {
        "name": "PROGRAM5",
        "title": "PROGRAM5.cbl - run output",
        "common_top": [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. PROGRAM5.",
            "DATA DIVISION.",
            "WORKING-STORAGE SECTION.",
            "01 WS-COUNTER  PIC 9(3) VALUE 0.",
            "PROCEDURE DIVISION.",
            "    PERFORM VARYING WS-COUNTER FROM 1 BY 1",
            "        UNTIL WS-COUNTER > 3",
            "        DISPLAY 'LOOP: ' WS-COUNTER",
            "    END-PERFORM.",
            "",
            "--- OUTPUT ---",
        ],
        "actual_line": "LOOP: 001  LOOP: 002  LOOP: 003  LOOP: 004",
        "expected_line": "LOOP: 001  LOOP: 002  LOOP: 003",
    },
]


def build(program, mode):
    lines = list(program["common_top"])
    lines.append(program["actual_line"] if mode == "actual" else program["expected_line"])
    return render_screen(program["name"], program["title"], lines)


for prog in PROGRAMS:
    actual_img = build(prog, "actual")
    expected_img = build(prog, "expected")
    actual_img.save(os.path.join(ACTUAL_DIR, f"{prog['name']}.png"))
    expected_img.save(os.path.join(EXPECTED_DIR, f"{prog['name']}.png"))
    print(f"Created {prog['name']}.png in both folders")

print("\nDone.")
print(f"Actual output images:   {ACTUAL_DIR}")
print(f"Expected output images: {EXPECTED_DIR}")
