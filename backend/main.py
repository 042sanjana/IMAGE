import io
import os
import uuid

from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from PIL import Image, ImageChops

from backend import word_diff


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="COBOL Image Diff Tool",
    description=(
        "Visual comparison of expected and actual "
        "COBOL terminal screenshots"
    ),
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DIRECTORIES
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

REPORT_DIR = os.path.join(
    BASE_DIR,
    "reports"
)

UI_REPORT_DIR = os.path.join(
    REPORT_DIR,
    "ui_reports"
)

os.makedirs(
    REPORT_DIR,
    exist_ok=True
)

os.makedirs(
    UI_REPORT_DIR,
    exist_ok=True
)


# =========================================================
# RUN DETAILS - TERMINAL
# =========================================================

def _print_run_details(
    status,
    start_time,
    end_time,
    processing_time,
    actual_count,
    expected_count,
    total_processed,
    images_compared,
    matched=0,
    changed=0,
    missing=0,
    extra=0
):
    print()
    print("=" * 60)
    print("COBOL IMAGE COMPARISON - RUN DETAILS")
    print("=" * 60)

    print(
        f"Status                  : {status}"
    )

    print(
        f"Start Time              : "
        f"{start_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"End Time                : "
        f"{end_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"Processing Time         : "
        f"{processing_time:.2f} seconds"
    )

    print(
        f"Actual Images           : "
        f"{actual_count}"
    )

    print(
        f"Expected Images         : "
        f"{expected_count}"
    )

    print(
        f"Total Images Processed  : "
        f"{total_processed}"
    )

    print(
        f"Images Compared         : "
        f"{images_compared}"
    )

    print(
        f"Matched                 : "
        f"{matched}"
    )

    print(
        f"Changed                 : "
        f"{changed}"
    )

    print(
        f"Missing                 : "
        f"{missing}"
    )

    print(
        f"Extra                   : "
        f"{extra}"
    )

    print("=" * 60)
    print()


# =========================================================
# FILENAME MATCHING
# =========================================================

def _basekey(filename: str) -> str:
    """
    Convert:

        PROGRAM1.png
        PROGRAM1.PNG
        program1.jpg

    into:

        program1
    """

    name = os.path.basename(
        filename
    )

    stem, _ext = os.path.splitext(
        name
    )

    return stem.strip().casefold()


# =========================================================
# IMAGE LOADING
# =========================================================

def _load_image(
    data: bytes
) -> Image.Image:

    try:

        image = Image.open(
            io.BytesIO(data)
        )

        return image.convert(
            "RGB"
        )

    except Exception as exc:

        raise ValueError(
            f"Invalid image: {exc}"
        )


# =========================================================
# ALIGN IMAGE SIZES
# =========================================================

def _align_sizes(
    actual: Image.Image,
    expected: Image.Image
):

    if actual.size == expected.size:

        return (
            actual,
            expected
        )

    width = max(
        actual.width,
        expected.width
    )

    height = max(
        actual.height,
        expected.height
    )

    canvas_actual = Image.new(
        "RGB",
        (width, height),
        (0, 0, 0)
    )

    canvas_expected = Image.new(
        "RGB",
        (width, height),
        (0, 0, 0)
    )

    canvas_actual.paste(
        actual,
        (0, 0)
    )

    canvas_expected.paste(
        expected,
        (0, 0)
    )

    return (
        canvas_actual,
        canvas_expected
    )


# =========================================================
# PIXEL DIFFERENCE
# =========================================================

def _compute_diff(
    actual_img: Image.Image,
    expected_img: Image.Image
):

    actual, expected = _align_sizes(
        actual_img,
        expected_img
    )

    diff = ImageChops.difference(
        actual,
        expected
    )

    gray = diff.convert(
        "L"
    )

    threshold = 30

    mask = gray.point(
        lambda p:
        255 if p > threshold
        else 0
    )

    mask_pixels = mask.load()

    changed_pixels = 0

    for y in range(mask.height):

        for x in range(mask.width):

            if mask_pixels[x, y] > 0:

                changed_pixels += 1

    total_pixels = (
        mask.width *
        mask.height
    )

    percent_changed = (
        round(
            (
                changed_pixels /
                total_pixels
            ) * 100,
            3
        )
        if total_pixels
        else 0
    )

    # -----------------------------------------------------
    # Red highlighted difference
    # -----------------------------------------------------

    overlay = expected.copy()

    overlay_pixels = overlay.load()

    for y in range(mask.height):

        for x in range(mask.width):

            if mask_pixels[x, y] > 0:

                overlay_pixels[x, y] = (
                    255,
                    0,
                    0
                )

    return {

        "actual":
            actual,

        "expected":
            expected,

        "overlay":
            overlay,

        "mask":
            mask,

        "changed_pixels":
            changed_pixels,

        "total_pixels":
            total_pixels,

        "percent_changed":
            percent_changed,
    }


# =========================================================
# SAVE PIL IMAGE
# =========================================================

def _save_pil_image(
    image: Image.Image,
    path: str
):

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    image.save(
        path,
        format="PNG"
    )


# =========================================================
# UI IMAGE URL
# =========================================================

def _ui_url(
    comparison_id: str,
    relative_path: str
):

    relative_path = relative_path.replace(
        os.sep,
        "/"
    )

    return (
        "/ui-images/"
        f"{comparison_id}/"
        f"{relative_path}"
    )


# =========================================================
# SAFE DIRECTORY NAME
# =========================================================

def _safe_name(
    name: str
):

    return "".join(
        character
        if (
            character.isalnum()
            or character in "._-"
        )
        else "_"
        for character in name
    )


# =========================================================
# SAVE UNMATCHED IMAGE
# =========================================================

def _save_unmatched_image(
    comparison_id: str,
    filename: str,
    image: Image.Image,
    folder_name: str
):

    safe_filename = _safe_name(
        filename
    )

    directory = os.path.join(
        UI_REPORT_DIR,
        comparison_id,
        folder_name
    )

    os.makedirs(
        directory,
        exist_ok=True
    )

    image_path = os.path.join(
        directory,
        safe_filename
    )

    _save_pil_image(
        image,
        image_path
    )

    return _ui_url(
        comparison_id,
        os.path.join(
            folder_name,
            safe_filename
        )
    )


# =========================================================
# SAVE UI PAIR
# =========================================================

def _save_ui_pair(
    comparison_id: str,
    pair_name: str,
    expected_img: Image.Image,
    actual_img: Image.Image,
    overlay_img: Image.Image,
    records
):

    safe_name = _safe_name(
        pair_name
    )

    pair_dir = os.path.join(
        UI_REPORT_DIR,
        comparison_id,
        safe_name
    )

    os.makedirs(
        pair_dir,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Full expected image
    # -----------------------------------------------------

    _save_pil_image(
        expected_img,
        os.path.join(
            pair_dir,
            "expected.png"
        )
    )

    # -----------------------------------------------------
    # Full actual image
    # -----------------------------------------------------

    _save_pil_image(
        actual_img,
        os.path.join(
            pair_dir,
            "actual.png"
        )
    )

    # -----------------------------------------------------
    # Difference image
    # -----------------------------------------------------

    _save_pil_image(
        overlay_img,
        os.path.join(
            pair_dir,
            "difference.png"
        )
    )

    # -----------------------------------------------------
    # Annotated images
    # -----------------------------------------------------

    expected_annotated = (
        word_diff.render_annotated(
            expected_img,
            records,
            "expected"
        )
    )

    actual_annotated = (
        word_diff.render_annotated(
            actual_img,
            records,
            "actual"
        )
    )

    _save_pil_image(
        expected_annotated,
        os.path.join(
            pair_dir,
            "expected_annotated.png"
        )
    )

    _save_pil_image(
        actual_annotated,
        os.path.join(
            pair_dir,
            "actual_annotated.png"
        )
    )

    # -----------------------------------------------------
    # UI line records
    # -----------------------------------------------------

    ui_lines = []

    for record in records:

        line_number = record[
            "line_number"
        ]

        line_status = record[
            "status"
        ]

        line_dir = os.path.join(
            pair_dir,
            f"line_{line_number:03d}"
        )

        os.makedirs(
            line_dir,
            exist_ok=True
        )

        # =================================================
        # Expected line crop
        # =================================================

        expected_words = [
            word["expected_word"]
            for word in record["words"]
            if word.get("expected_word")
        ]

        expected_line_url = None

        if expected_words:

            min_y = min(
                word["y0"]
                for word in expected_words
            )

            max_y = max(
                word["y1"]
                for word in expected_words
            )

            expected_line_crop = (
                expected_img.crop(
                    (
                        0,
                        max(0, min_y - 8),
                        expected_img.width,
                        min(
                            expected_img.height,
                            max_y + 8
                        )
                    )
                )
            )

            expected_line_file = (
                "expected_line.png"
            )

            _save_pil_image(
                expected_line_crop,
                os.path.join(
                    line_dir,
                    expected_line_file
                )
            )

            expected_line_url = _ui_url(
                comparison_id,
                os.path.join(
                    safe_name,
                    f"line_{line_number:03d}",
                    expected_line_file
                )
            )

        # =================================================
        # Actual line crop
        # =================================================

        actual_words = [
            word["actual_word"]
            for word in record["words"]
            if word.get("actual_word")
        ]

        actual_line_url = None

        if actual_words:

            min_y = min(
                word["y0"]
                for word in actual_words
            )

            max_y = max(
                word["y1"]
                for word in actual_words
            )

            actual_line_crop = (
                actual_img.crop(
                    (
                        0,
                        max(0, min_y - 8),
                        actual_img.width,
                        min(
                            actual_img.height,
                            max_y + 8
                        )
                    )
                )
            )

            actual_line_file = (
                "actual_line.png"
            )

            _save_pil_image(
                actual_line_crop,
                os.path.join(
                    line_dir,
                    actual_line_file
                )
            )

            actual_line_url = _ui_url(
                comparison_id,
                os.path.join(
                    safe_name,
                    f"line_{line_number:03d}",
                    actual_line_file
                )
            )

        # =================================================
        # Words
        # =================================================

        ui_words = []

        for word_index, word in enumerate(
            record["words"],
            start=1
        ):

            status = word[
                "status"
            ]

            expected_url = None
            actual_url = None

            # ---------------------------------------------
            # Expected word crop
            # ---------------------------------------------

            if word.get(
                "expected_word"
            ):

                crop = word_diff.crop_word(
                    expected_img,
                    word["expected_word"]
                )

                filename = (
                    f"W{word_index:03d}_expected.png"
                )

                _save_pil_image(
                    crop,
                    os.path.join(
                        line_dir,
                        filename
                    )
                )

                expected_url = _ui_url(
                    comparison_id,
                    os.path.join(
                        safe_name,
                        f"line_{line_number:03d}",
                        filename
                    )
                )

            # ---------------------------------------------
            # Actual word crop
            # ---------------------------------------------

            if word.get(
                "actual_word"
            ):

                crop = word_diff.crop_word(
                    actual_img,
                    word["actual_word"]
                )

                filename = (
                    f"W{word_index:03d}_actual.png"
                )

                _save_pil_image(
                    crop,
                    os.path.join(
                        line_dir,
                        filename
                    )
                )

                actual_url = _ui_url(
                    comparison_id,
                    os.path.join(
                        safe_name,
                        f"line_{line_number:03d}",
                        filename
                    )
                )

            ui_words.append({

                "word_number":
                    word_index,

                "status":
                    status,

                "expected_image":
                    expected_url,

                "actual_image":
                    actual_url
            })

        ui_lines.append({

            "line_number":
                line_number,

            "status":
                line_status,

            "expected_line":
                expected_line_url,

            "actual_line":
                actual_line_url,

            "words":
                ui_words
        })

    return {

        "expected_image":
            _ui_url(
                comparison_id,
                os.path.join(
                    safe_name,
                    "expected.png"
                )
            ),

        "actual_image":
            _ui_url(
                comparison_id,
                os.path.join(
                    safe_name,
                    "actual.png"
                )
            ),

        "difference_image":
            _ui_url(
                comparison_id,
                os.path.join(
                    safe_name,
                    "difference.png"
                )
            ),

        "expected_annotated":
            _ui_url(
                comparison_id,
                os.path.join(
                    safe_name,
                    "expected_annotated.png"
                )
            ),

        "actual_annotated":
            _ui_url(
                comparison_id,
                os.path.join(
                    safe_name,
                    "actual_annotated.png"
                )
            ),

        "lines":
            ui_lines
    }


# =========================================================
# WORD REPORT
# =========================================================

def _create_word_report(
    report_data,
    output_path
):

    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    document = Document()

    # -----------------------------------------------------
    # Title
    # -----------------------------------------------------

    title = document.add_heading(
        "COBOL IMAGE COMPARISON REPORT",
        0
    )

    title.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    p = document.add_paragraph()

    p.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = p.add_run(
        "Expected Output vs Actual Output"
    )

    run.bold = True
    run.font.size = Pt(14)

    document.add_paragraph(
        f"Generated: "
        f"{report_data['generated_at']}"
    )

    # =====================================================
    # RUN DETAILS
    # =====================================================

    run_details = report_data.get(
        "run_details",
        {}
    )

    if run_details:

        document.add_heading(
            "Run Details",
            level=1
        )

        run_table = document.add_table(
            rows=1,
            cols=2
        )

        run_table.alignment = (
            WD_TABLE_ALIGNMENT.CENTER
        )

        run_table.style = "Table Grid"

        run_hdr = run_table.rows[0].cells

        run_hdr[0].text = "Run Information"
        run_hdr[1].text = "Value"

        run_rows = [

            (
                "Status",
                run_details.get(
                    "status",
                    "-"
                )
            ),

            (
                "Start Time",
                run_details.get(
                    "start_time",
                    "-"
                )
            ),

            (
                "End Time",
                run_details.get(
                    "end_time",
                    "-"
                )
            ),

            (
                "Processing Time",
                run_details.get(
                    "processing_time",
                    "-"
                )
            ),

            (
                "Actual Images",
                run_details.get(
                    "actual_images",
                    0
                )
            ),

            (
                "Expected Images",
                run_details.get(
                    "expected_images",
                    0
                )
            ),

            (
                "Total Images Processed",
                run_details.get(
                    "total_images_processed",
                    0
                )
            ),

            (
                "Images Compared",
                run_details.get(
                    "images_compared",
                    0
                )
            ),

            (
                "Matched",
                run_details.get(
                    "matched",
                    0
                )
            ),

            (
                "Changed",
                run_details.get(
                    "changed",
                    0
                )
            ),

            (
                "Missing",
                run_details.get(
                    "missing",
                    0
                )
            ),

            (
                "Extra",
                run_details.get(
                    "extra",
                    0
                )
            ),
        ]

        for name, value in run_rows:

            row = run_table.add_row().cells

            row[0].text = str(name)
            row[1].text = str(value)

        document.add_paragraph()

    # -----------------------------------------------------
    # Overall summary
    # -----------------------------------------------------

    document.add_heading(
        "Overall Summary",
        level=1
    )

    summary = report_data[
        "summary"
    ]

    table = document.add_table(
        rows=1,
        cols=2
    )

    table.alignment = (
        WD_TABLE_ALIGNMENT.CENTER
    )

    table.style = "Table Grid"

    hdr = table.rows[0].cells

    hdr[0].text = "Metric"
    hdr[1].text = "Value"

    summary_rows = [

        (
            "Expected images",
            summary["expected"]
        ),

        (
            "Actual images",
            summary["actual"]
        ),

        (
            "Matched filenames",
            summary["matched"]
        ),

        (
            "Changed",
            summary["changed"]
        ),

        (
            "Identical",
            summary["identical"]
        ),

        (
            "Missing",
            summary["missing"]
        ),

        (
            "Extra",
            summary["extra"]
        ),
    ]

    for name, value in summary_rows:

        row = table.add_row().cells

        row[0].text = str(name)
        row[1].text = str(value)

    document.add_paragraph()

    document.add_paragraph(
        "Note: This is a visual comparison. "
        "No OCR is used. Changed areas are "
        "shown using the original image pixels."
    )

    # -----------------------------------------------------
    # Image pairs
    # -----------------------------------------------------

    for pair in report_data[
        "pairs"
    ]:

        document.add_page_break()

        filename = pair[
            "filename"
        ]

        document.add_heading(
            filename,
            level=1
        )

        status = pair[
            "status"
        ]

        p = document.add_paragraph()

        run = p.add_run(
            f"STATUS: {status}"
        )

        run.bold = True
        run.font.size = Pt(14)

        document.add_paragraph(
            "Pixel difference: "
            f"{pair['percent_pixels_changed']}%"
        )

        document.add_paragraph(
            "Changed regions: "
            f"{pair['num_changed_regions']}"
        )

        # -------------------------------------------------
        # Expected
        # -------------------------------------------------

        document.add_heading(
            "EXPECTED IMAGE",
            level=2
        )

        expected_buf = io.BytesIO()

        pair[
            "expected_image"
        ].save(
            expected_buf,
            format="PNG"
        )

        expected_buf.seek(0)

        document.add_picture(
            expected_buf,
            width=Inches(6.5)
        )

        # -------------------------------------------------
        # Actual
        # -------------------------------------------------

        document.add_heading(
            "ACTUAL IMAGE",
            level=2
        )

        actual_buf = io.BytesIO()

        pair[
            "actual_image"
        ].save(
            actual_buf,
            format="PNG"
        )

        actual_buf.seek(0)

        document.add_picture(
            actual_buf,
            width=Inches(6.5)
        )

        # -------------------------------------------------
        # Difference
        # -------------------------------------------------

        document.add_heading(
            "DIFFERENCE",
            level=2
        )

        diff_buf = io.BytesIO()

        pair[
            "overlay_image"
        ].save(
            diff_buf,
            format="PNG"
        )

        diff_buf.seek(0)

        document.add_picture(
            diff_buf,
            width=Inches(6.5)
        )

        # -------------------------------------------------
        # Changes
        # -------------------------------------------------

        document.add_heading(
            "CHANGES FOUND",
            level=2
        )

        changes = pair[
            "changes"
        ]

        if not changes:

            document.add_paragraph(
                "No changes detected."
            )

            continue

        for change in changes:

            document.add_heading(
                f"Line "
                f"{change['line_number']} "
                f"- "
                f"{change['status'].upper()}",
                level=3
            )

            for word_index, word in enumerate(
                change["words"],
                start=1
            ):

                if word["status"] == "matched":
                    continue

                p = document.add_paragraph()

                r = p.add_run(
                    f"Word {word_index}: "
                    f"{word['status'].upper()}"
                )

                r.bold = True

                word_table = document.add_table(
                    rows=2,
                    cols=2
                )

                word_table.style = (
                    "Table Grid"
                )

                word_table.cell(
                    0,
                    0
                ).text = "EXPECTED"

                word_table.cell(
                    0,
                    1
                ).text = "ACTUAL"

                # -----------------------------------------
                # Expected crop
                # -----------------------------------------

                if word.get(
                    "expected_word"
                ):

                    crop = word_diff.crop_word(
                        pair[
                            "expected_image"
                        ],
                        word[
                            "expected_word"
                        ]
                    )

                    expected_crop = (
                        io.BytesIO()
                    )

                    crop.save(
                        expected_crop,
                        format="PNG"
                    )

                    expected_crop.seek(0)

                    paragraph = (
                        word_table
                        .cell(1, 0)
                        .paragraphs[0]
                    )

                    paragraph.add_run().add_picture(
                        expected_crop,
                        width=Inches(2.5)
                    )

                else:

                    word_table.cell(
                        1,
                        0
                    ).text = (
                        "Not present"
                    )

                # -----------------------------------------
                # Actual crop
                # -----------------------------------------

                if word.get(
                    "actual_word"
                ):

                    crop = word_diff.crop_word(
                        pair[
                            "actual_image"
                        ],
                        word[
                            "actual_word"
                        ]
                    )

                    actual_crop = (
                        io.BytesIO()
                    )

                    crop.save(
                        actual_crop,
                        format="PNG"
                    )

                    actual_crop.seek(0)

                    paragraph = (
                        word_table
                        .cell(1, 1)
                        .paragraphs[0]
                    )

                    paragraph.add_run().add_picture(
                        actual_crop,
                        width=Inches(2.5)
                    )

                else:

                    word_table.cell(
                        1,
                        1
                    ).text = (
                        "Not present"
                    )

                document.add_paragraph()

    # -----------------------------------------------------
    # Unmatched expected
    # -----------------------------------------------------

    if report_data[
        "unmatched_expected"
    ]:

        document.add_page_break()

        document.add_heading(
            "Expected Images Without "
            "Matching Actual Image",
            level=1
        )

        for filename in report_data[
            "unmatched_expected"
        ]:

            document.add_paragraph(
                filename
            )

    # -----------------------------------------------------
    # Unmatched actual
    # -----------------------------------------------------

    if report_data[
        "unmatched_actual"
    ]:

        document.add_heading(
            "Actual Images Without "
            "Matching Expected Image",
            level=1
        )

        for filename in report_data[
            "unmatched_actual"
        ]:

            document.add_paragraph(
                filename
            )

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    document.save(
        output_path
    )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {

        "service":
            "COBOL Image Diff Tool",

        "status":
            "running",

        "frontend":
            "Streamlit",

        "report_format":
            "DOCX"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status":
            "ok"
    }


# =========================================================
# SERVE UI IMAGE
# =========================================================

@app.get(
    "/ui-images/{comparison_id}/{file_path:path}"
)
def get_ui_image(
    comparison_id: str,
    file_path: str
):

    base_dir = os.path.abspath(
        os.path.join(
            UI_REPORT_DIR,
            comparison_id
        )
    )

    requested_path = os.path.abspath(
        os.path.join(
            base_dir,
            file_path
        )
    )

    # Security: prevent ../ traversal
    if not requested_path.startswith(
        base_dir + os.sep
    ):

        raise HTTPException(
            status_code=403,
            detail="Invalid image path."
        )

    if not os.path.isfile(
        requested_path
    ):

        raise HTTPException(
            status_code=404,
            detail="Image not found."
        )

    return FileResponse(
        requested_path,
        media_type="image/png"
    )


# =========================================================
# COMPARE
# =========================================================

@app.post("/compare")
async def compare(
    actual: List[UploadFile] = File(...),
    expected: List[UploadFile] = File(...)
):

    # =====================================================
    # RUN START
    # =====================================================

    run_start = datetime.now()

    # =====================================================
    # Initial validation
    # =====================================================

    if not actual:

        run_end = datetime.now()

        _print_run_details(
            "FAILED",
            run_start,
            run_end,
            (
                run_end - run_start
            ).total_seconds(),
            0,
            len(expected) if expected else 0,
            0,
            0
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Please upload actual images."
            )
        )

    if not expected:

        run_end = datetime.now()

        _print_run_details(
            "FAILED",
            run_start,
            run_end,
            (
                run_end - run_start
            ).total_seconds(),
            len(actual) if actual else 0,
            0,
            0,
            0
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Please upload expected images."
            )
        )

    # =====================================================
    # Read actual files
    # =====================================================

    actual_bytes = {}

    for file in actual:

        if not file.filename:
            continue

        actual_bytes[
            file.filename
        ] = await file.read()

    # =====================================================
    # Read expected files
    # =====================================================

    expected_bytes = {}

    for file in expected:

        if not file.filename:
            continue

        expected_bytes[
            file.filename
        ] = await file.read()

    if not actual_bytes:

        run_end = datetime.now()

        _print_run_details(
            "FAILED",
            run_start,
            run_end,
            (
                run_end - run_start
            ).total_seconds(),
            0,
            len(expected_bytes),
            0,
            0
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "No valid actual images uploaded."
            )
        )

    if not expected_bytes:

        run_end = datetime.now()

        _print_run_details(
            "FAILED",
            run_start,
            run_end,
            (
                run_end - run_start
            ).total_seconds(),
            len(actual_bytes),
            0,
            0,
            0
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "No valid expected images uploaded."
            )
        )

    # =====================================================
    # Filename matching
    # =====================================================

    actual_by_key = {

        _basekey(name):
            name

        for name in actual_bytes
    }

    expected_by_key = {

        _basekey(name):
            name

        for name in expected_bytes
    }

    all_keys = sorted(
        set(actual_by_key)
        |
        set(expected_by_key)
    )

    # =====================================================
    # Comparison ID
    # =====================================================

    comparison_id = (
        "comparison_"
        + datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        + "_"
        + uuid.uuid4().hex[:8]
    )

    # =====================================================
    # Report structure
    # =====================================================

    report = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "summary": {

            "actual":
                len(actual_bytes),

            "expected":
                len(expected_bytes),

            "matched":
                0,

            "changed":
                0,

            "identical":
                0,

            "missing":
                0,

            "extra":
                0
        },

        "pairs": [],

        "unmatched_actual": [],

        "unmatched_expected": []
    }

    # =====================================================
    # Compare each filename
    # =====================================================

    for key in all_keys:

        actual_name = (
            actual_by_key.get(key)
        )

        expected_name = (
            expected_by_key.get(key)
        )

        # =================================================
        # EXTRA ACTUAL
        # =================================================

        if actual_name and not expected_name:

            report[
                "unmatched_actual"
            ].append(
                actual_name
            )

            report[
                "summary"
            ]["extra"] += 1

            try:

                actual_img = _load_image(
                    actual_bytes[
                        actual_name
                    ]
                )

                actual_url = (
                    _save_unmatched_image(
                        comparison_id,
                        actual_name,
                        actual_img,
                        "extra_actual"
                    )
                )

            except Exception:

                actual_url = None

            report.setdefault(
                "unmatched_actual_details",
                []
            ).append({

                "filename":
                    actual_name,

                "status":
                    "EXTRA",

                "image":
                    actual_url
            })

            continue

        # =================================================
        # MISSING ACTUAL
        # =================================================

        if expected_name and not actual_name:

            report[
                "unmatched_expected"
            ].append(
                expected_name
            )

            report[
                "summary"
            ]["missing"] += 1

            try:

                expected_img = _load_image(
                    expected_bytes[
                        expected_name
                    ]
                )

                expected_url = (
                    _save_unmatched_image(
                        comparison_id,
                        expected_name,
                        expected_img,
                        "missing_actual"
                    )
                )

            except Exception:

                expected_url = None

            report.setdefault(
                "unmatched_expected_details",
                []
            ).append({

                "filename":
                    expected_name,

                "status":
                    "MISSING",

                "image":
                    expected_url
            })

            continue

        # =================================================
        # Both exist
        # =================================================

        try:

            actual_img = _load_image(
                actual_bytes[
                    actual_name
                ]
            )

            expected_img = _load_image(
                expected_bytes[
                    expected_name
                ]
            )

        except Exception as exc:

            run_end = datetime.now()

            _print_run_details(
                "FAILED",
                run_start,
                run_end,
                (
                    run_end - run_start
                ).total_seconds(),
                len(actual_bytes),
                len(expected_bytes),
                (
                    len(actual_bytes)
                    +
                    len(expected_bytes)
                ),
                report["summary"]["matched"]
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Could not read "
                    f"{key}: {exc}"
                )
            )

        report[
            "summary"
        ]["matched"] += 1

        # =================================================
        # Pixel comparison
        # =================================================

        diff = _compute_diff(
            actual_img,
            expected_img
        )

        percent_changed = (
            diff[
                "percent_changed"
            ]
        )

        if percent_changed == 0:

            status = "MATCH"

            report[
                "summary"
            ]["identical"] += 1

        else:

            status = "CHANGED"

            report[
                "summary"
            ]["changed"] += 1

        # =================================================
        # Line detection
        # =================================================

        actual_lines = (
            word_diff.build_lines(
                actual_img
            )
        )

        expected_lines = (
            word_diff.build_lines(
                expected_img
            )
        )

        # =================================================
        # Word/line comparison
        # =================================================

        line_records = (
            word_diff.diff_lines(
                actual_lines,
                expected_lines,
                actual_img,
                expected_img
            )
        )

        changes = []

        for record in line_records:

            if record[
                "status"
            ] != "matched":

                changes.append(
                    record
                )

        # =================================================
        # Save UI data
        # =================================================

        ui_pair = _save_ui_pair(

            comparison_id=
                comparison_id,

            pair_name=
                expected_name,

            expected_img=
                expected_img,

            actual_img=
                actual_img,

            overlay_img=
                diff["overlay"],

            records=
                line_records
        )

        # =================================================
        # Add pair
        # =================================================

        report[
            "pairs"
        ].append({

            "filename":
                expected_name,

            "actual_filename":
                actual_name,

            "expected_filename":
                expected_name,

            "status":
                status,

            "percent_pixels_changed":
                percent_changed,

            "num_changed_regions":
                0,

            "expected_image":
                expected_img,

            "actual_image":
                actual_img,

            "overlay_image":
                diff["overlay"],

            "changes":
                changes,

            "ui":
                ui_pair
        })

    # =====================================================
    # RUN END
    #
    # IMPORTANT:
    # Calculate these BEFORE creating the Word report
    # so the same details can be written into the DOCX.
    # =====================================================

    run_end = datetime.now()

    processing_time = (
        run_end - run_start
    ).total_seconds()

    actual_count = len(
        actual_bytes
    )

    expected_count = len(
        expected_bytes
    )

    total_images_processed = (
        actual_count +
        expected_count
    )

    images_compared = (
        report[
            "summary"
        ]["matched"]
    )

    # =====================================================
    # RUN DETAILS
    # =====================================================

    run_details = {

        "status":
            "COMPLETED",

        "start_time":
            run_start.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "end_time":
            run_end.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "processing_time_seconds":
            round(
                processing_time,
                2
            ),

        "processing_time":
            f"{processing_time:.2f} seconds",

        "actual_images":
            actual_count,

        "expected_images":
            expected_count,

        "total_images_processed":
            total_images_processed,

        "images_compared":
            images_compared,

        "matched":
            report[
                "summary"
            ]["matched"],

        "changed":
            report[
                "summary"
            ]["changed"],

        "missing":
            report[
                "summary"
            ]["missing"],

        "extra":
            report[
                "summary"
            ]["extra"]
    }

    # =====================================================
    # ADD RUN DETAILS TO REPORT DATA
    # =====================================================

    report[
        "run_details"
    ] = run_details

    # =====================================================
    # WORD REPORT FILENAME
    # =====================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_filename = (
        "cobol_comparison_report_"
        f"{timestamp}.docx"
    )

    report_path = os.path.join(
        REPORT_DIR,
        report_filename
    )

    # =====================================================
    # CREATE WORD REPORT
    # =====================================================

    _create_word_report(
        report,
        report_path
    )

    # =====================================================
    # TERMINAL RUN DETAILS
    # =====================================================

    _print_run_details(

        status="COMPLETED",

        start_time=
            run_start,

        end_time=
            run_end,

        processing_time=
            processing_time,

        actual_count=
            actual_count,

        expected_count=
            expected_count,

        total_processed=
            total_images_processed,

        images_compared=
            images_compared,

        matched=
            report[
                "summary"
            ]["matched"],

        changed=
            report[
                "summary"
            ]["changed"],

        missing=
            report[
                "summary"
            ]["missing"],

        extra=
            report[
                "summary"
            ]["extra"]
    )

    # =====================================================
    # STREAMLIT RESPONSE
    # =====================================================

    response_pairs = []

    for pair in report[
        "pairs"
    ]:

        response_pairs.append({

            "filename":
                pair["filename"],

            "actual_filename":
                pair["actual_filename"],

            "expected_filename":
                pair["expected_filename"],

            "status":
                pair["status"],

            "percent_pixels_changed":
                pair[
                    "percent_pixels_changed"
                ],

            "changes_count":
                len(
                    pair["changes"]
                ),

            "expected_image":
                pair[
                    "ui"
                ][
                    "expected_image"
                ],

            "actual_image":
                pair[
                    "ui"
                ][
                    "actual_image"
                ],

            "difference_image":
                pair[
                    "ui"
                ][
                    "difference_image"
                ],

            "expected_annotated":
                pair[
                    "ui"
                ][
                    "expected_annotated"
                ],

            "actual_annotated":
                pair[
                    "ui"
                ][
                    "actual_annotated"
                ],

            "lines":
                pair[
                    "ui"
                ][
                    "lines"
                ]
        })

    # =====================================================
    # RETURN
    # =====================================================

    return {

        "message":
            "Comparison completed successfully.",

        "comparison_id":
            comparison_id,

        "report_filename":
            report_filename,

        "download_url":
            f"/reports/{report_filename}",

        "run_details":
            run_details,

        "summary":
            report["summary"],

        "pairs":
            response_pairs,

        "unmatched_actual":
            report[
                "unmatched_actual"
            ],

        "unmatched_expected":
            report[
                "unmatched_expected"
            ],

        "unmatched_actual_details":
            report.get(
                "unmatched_actual_details",
                []
            ),

        "unmatched_expected_details":
            report.get(
                "unmatched_expected_details",
                []
            )
    }


# =========================================================
# DOWNLOAD WORD REPORT
# =========================================================

@app.get(
    "/reports/{filename}"
)
def download_report(
    filename: str
):

    safe_filename = os.path.basename(
        filename
    )

    path = os.path.join(
        REPORT_DIR,
        safe_filename
    )

    if not os.path.isfile(path):

        raise HTTPException(
            status_code=404,
            detail="Report not found."
        )

    return FileResponse(
        path,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),
        filename=safe_filename
    )