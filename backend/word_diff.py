"""
word_diff.py

Line-by-line, word-by-word comparison between two COBOL screenshot images
using ONLY Pillow.

No OCR engine is used.

Words are detected using pixel geometry.
"""

import difflib
from typing import List, Dict, Any, Tuple

from PIL import Image, ImageDraw, ImageFont


# =========================================================
# TUNABLES
# =========================================================

MIN_LINE_HEIGHT = 5

MIN_WORD_WIDTH = 2

LINE_ROW_GAP = 0

WORD_COL_GAP = 5

LINE_SIG_SIZE = (
    96,
    12
)

WORD_SIG_SIZE = (
    24,
    14
)

QUANT_LEVELS = 6


# =========================================================
# OTSU
# =========================================================

def _otsu_threshold(
    gray_img: Image.Image
) -> int:

    hist = gray_img.histogram()

    total = sum(hist)

    sum_total = sum(
        i * hist[i]
        for i in range(256)
    )

    sum_b = 0.0

    w_b = 0

    max_var = -1.0

    threshold = 127

    for i in range(256):

        w_b += hist[i]

        if w_b == 0:
            continue

        w_f = total - w_b

        if w_f == 0:
            break

        sum_b += (
            i *
            hist[i]
        )

        m_b = (
            sum_b /
            w_b
        )

        m_f = (
            sum_total -
            sum_b
        ) / w_f

        var_between = (
            w_b *
            w_f *
            (m_b - m_f) ** 2
        )

        if var_between > max_var:

            max_var = (
                var_between
            )

            threshold = i

    return threshold


# =========================================================
# FOREGROUND MASK
# =========================================================

def foreground_mask(
    img: Image.Image
) -> Image.Image:

    gray = img.convert(
        "L"
    )

    threshold = (
        _otsu_threshold(
            gray
        )
    )

    hist = gray.histogram()

    below = sum(
        hist[
            :threshold + 1
        ]
    )

    above = sum(
        hist[
            threshold + 1:
        ]
    )

    if below <= above:

        mask = gray.point(
            lambda p:
            255
            if p <= threshold
            else 0
        )

    else:

        mask = gray.point(
            lambda p:
            255
            if p > threshold
            else 0
        )

    return mask


# =========================================================
# LINE SEGMENTATION
# =========================================================

def segment_lines(
    mask: Image.Image
) -> List[
    Tuple[int, int]
]:

    width, height = (
        mask.size
    )

    px = mask.load()

    row_has_fg = []

    for y in range(height):

        found = False

        for x in range(
            0,
            width,
            2
        ):

            if px[x, y]:

                found = True

                break

        row_has_fg.append(
            found
        )

    bands = []

    y = 0

    while y < height:

        if row_has_fg[y]:

            y0 = y

            while (
                y < height
                and
                row_has_fg[y]
            ):

                y += 1

            if (
                y - y0
                >= MIN_LINE_HEIGHT
            ):

                bands.append(
                    (
                        y0,
                        y
                    )
                )

        else:

            y += 1

    return bands


# =========================================================
# WORD SEGMENTATION
# =========================================================

def segment_words(
    mask: Image.Image,
    y0: int,
    y1: int
) -> List[
    Tuple[int, int]
]:

    width = mask.width

    px = mask.load()

    col_has_fg = []

    for x in range(width):

        found = False

        for y in range(
            y0,
            y1
        ):

            if px[x, y]:

                found = True

                break

        col_has_fg.append(
            found
        )

    boxes = []

    x = 0

    while x < width:

        if col_has_fg[x]:

            x0 = x

            gap = 0

            xx = x

            last_fg = x

            while xx < width:

                if col_has_fg[xx]:

                    gap = 0

                    last_fg = xx

                else:

                    gap += 1

                    if (
                        gap >
                        WORD_COL_GAP
                    ):

                        break

                xx += 1

            x1 = (
                last_fg +
                1
            )

            if (
                x1 - x0
                >= MIN_WORD_WIDTH
            ):

                boxes.append(
                    (
                        x0,
                        x1
                    )
                )

            x = xx

        else:

            x += 1

    return boxes


# =========================================================
# BUILD LINES
# =========================================================

def build_lines(
    img: Image.Image
) -> List[
    Dict[str, Any]
]:

    mask = foreground_mask(
        img
    )

    lines = []

    for (
        y0,
        y1
    ) in segment_lines(
        mask
    ):

        words = [

            {
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1
            }

            for (
                x0,
                x1
            ) in segment_words(
                mask,
                y0,
                y1
            )
        ]

        lines.append({

            "y0":
                y0,

            "y1":
                y1,

            "words":
                words
        })

    return lines


# =========================================================
# SIGNATURE
# =========================================================

def _quantized_signature(
    crop: Image.Image,
    size
) -> tuple:

    small = (
        crop
        .convert("L")
        .resize(size)
    )

    step = (
        256 //
        QUANT_LEVELS
    )

    return tuple(

        min(
            value // step,
            QUANT_LEVELS - 1
        )

        for value
        in small.getdata()
    )


# =========================================================
# LINE SIGNATURE
# =========================================================

def line_signature(
    img: Image.Image,
    line: Dict[str, Any]
) -> tuple:

    crop = img.crop(
        (
            0,
            line["y0"],
            img.width,
            line["y1"]
        )
    )

    return _quantized_signature(
        crop,
        LINE_SIG_SIZE
    )


# =========================================================
# WORD SIGNATURE
# =========================================================

def word_signature(
    img: Image.Image,
    word: Dict[str, Any]
) -> tuple:

    pad = 1

    box = (

        max(
            0,
            word["x0"] - pad
        ),

        max(
            0,
            word["y0"] - pad
        ),

        min(
            img.width,
            word["x1"] + pad
        ),

        min(
            img.height,
            word["y1"] + pad
        )
    )

    crop = img.crop(
        box
    )

    return _quantized_signature(
        crop,
        WORD_SIG_SIZE
    )


# =========================================================
# CROP WORD
# =========================================================

def crop_word(
    img: Image.Image,
    word: Dict[str, Any],
    pad: int = 3
) -> Image.Image:

    box = (

        max(
            0,
            word["x0"] - pad
        ),

        max(
            0,
            word["y0"] - pad
        ),

        min(
            img.width,
            word["x1"] + pad
        ),

        min(
            img.height,
            word["y1"] + pad
        )
    )

    return img.crop(
        box
    )


# =========================================================
# WORD DIFF
# =========================================================

def _word_diff_record(
    line_no: int,
    exp_words,
    act_words,
    exp_img,
    act_img
) -> Dict[str, Any]:

    exp_sigs = [

        word_signature(
            exp_img,
            word
        )

        for word
        in exp_words
    ]

    act_sigs = [

        word_signature(
            act_img,
            word
        )

        for word
        in act_words
    ]

    matcher = (
        difflib.SequenceMatcher(
            a=exp_sigs,
            b=act_sigs,
            autojunk=False
        )
    )

    words = []

    for (
        tag,
        e1,
        e2,
        a1,
        a2
    ) in matcher.get_opcodes():

        # -------------------------------------------------
        # Equal
        # -------------------------------------------------

        if tag == "equal":

            for (
                e_i,
                a_i
            ) in zip(
                range(e1, e2),
                range(a1, a2)
            ):

                words.append({

                    "status":
                        "matched",

                    "expected_word":
                        exp_words[e_i],

                    "actual_word":
                        act_words[a_i]
                })

        # -------------------------------------------------
        # Replace
        # -------------------------------------------------

        elif tag == "replace":

            e_idx = list(
                range(
                    e1,
                    e2
                )
            )

            a_idx = list(
                range(
                    a1,
                    a2
                )
            )

            for (
                e_i,
                a_i
            ) in zip(
                e_idx,
                a_idx
            ):

                words.append({

                    "status":
                        "changed",

                    "expected_word":
                        exp_words[e_i],

                    "actual_word":
                        act_words[a_i]
                })

            for e_i in e_idx[
                len(a_idx):
            ]:

                words.append({

                    "status":
                        "missing",

                    "expected_word":
                        exp_words[e_i],

                    "actual_word":
                        None
                })

            for a_i in a_idx[
                len(e_idx):
            ]:

                words.append({

                    "status":
                        "extra",

                    "expected_word":
                        None,

                    "actual_word":
                        act_words[a_i]
                })

        # -------------------------------------------------
        # Delete
        # -------------------------------------------------

        elif tag == "delete":

            for e_i in range(
                e1,
                e2
            ):

                words.append({

                    "status":
                        "missing",

                    "expected_word":
                        exp_words[e_i],

                    "actual_word":
                        None
                })

        # -------------------------------------------------
        # Insert
        # -------------------------------------------------

        elif tag == "insert":

            for a_i in range(
                a1,
                a2
            ):

                words.append({

                    "status":
                        "extra",

                    "expected_word":
                        None,

                    "actual_word":
                        act_words[a_i]
                })

    has_change = any(
        word["status"]
        != "matched"
        for word in words
    )

    return {

        "line_number":
            line_no,

        "status":
            (
                "changed"
                if has_change
                else "matched"
            ),

        "words":
            words
    }


# =========================================================
# LINE DIFF
# =========================================================

def diff_lines(
    actual_lines: List[Dict],
    expected_lines: List[Dict],
    actual_img: Image.Image,
    expected_img: Image.Image
) -> List[
    Dict[str, Any]
]:

    expected_signatures = [

        line_signature(
            expected_img,
            line
        )

        for line
        in expected_lines
    ]

    actual_signatures = [

        line_signature(
            actual_img,
            line
        )

        for line
        in actual_lines
    ]

    matcher = (
        difflib.SequenceMatcher(
            a=expected_signatures,
            b=actual_signatures,
            autojunk=False
        )
    )

    records = []

    line_no = 0

    for (
        tag,
        e1,
        e2,
        a1,
        a2
    ) in matcher.get_opcodes():

        # -------------------------------------------------
        # Equal
        # -------------------------------------------------

        if tag == "equal":

            for (
                e_i,
                a_i
            ) in zip(
                range(e1, e2),
                range(a1, a2)
            ):

                line_no += 1

                words = [

                    {
                        "status":
                            "matched",

                        "expected_word":
                            word,

                        "actual_word":
                            word
                    }

                    for word
                    in expected_lines[
                        e_i
                    ][
                        "words"
                    ]
                ]

                records.append({

                    "line_number":
                        line_no,

                    "status":
                        "matched",

                    "words":
                        words
                })

        # -------------------------------------------------
        # Replace
        # -------------------------------------------------

        elif tag == "replace":

            expected_block = list(
                range(
                    e1,
                    e2
                )
            )

            actual_block = list(
                range(
                    a1,
                    a2
                )
            )

            paired = list(
                zip(
                    expected_block,
                    actual_block
                )
            )

            for (
                e_i,
                a_i
            ) in paired:

                line_no += 1

                record = (
                    _word_diff_record(
                        line_no,

                        expected_lines[
                            e_i
                        ]["words"],

                        actual_lines[
                            a_i
                        ]["words"],

                        expected_img,
                        actual_img
                    )
                )

                records.append(
                    record
                )

            # Remaining expected lines
            for e_i in expected_block[
                len(paired):
            ]:

                line_no += 1

                words = [

                    {
                        "status":
                            "missing",

                        "expected_word":
                            word,

                        "actual_word":
                            None
                    }

                    for word
                    in expected_lines[
                        e_i
                    ][
                        "words"
                    ]
                ]

                records.append({

                    "line_number":
                        line_no,

                    "status":
                        "missing",

                    "words":
                        words
                })

            # Remaining actual lines
            for a_i in actual_block[
                len(paired):
            ]:

                line_no += 1

                words = [

                    {
                        "status":
                            "extra",

                        "expected_word":
                            None,

                        "actual_word":
                            word
                    }

                    for word
                    in actual_lines[
                        a_i
                    ][
                        "words"
                    ]
                ]

                records.append({

                    "line_number":
                        line_no,

                    "status":
                        "extra",

                    "words":
                        words
                })

        # -------------------------------------------------
        # Delete
        # -------------------------------------------------

        elif tag == "delete":

            for e_i in range(
                e1,
                e2
            ):

                line_no += 1

                words = [

                    {
                        "status":
                            "missing",

                        "expected_word":
                            word,

                        "actual_word":
                            None
                    }

                    for word
                    in expected_lines[
                        e_i
                    ][
                        "words"
                    ]
                ]

                records.append({

                    "line_number":
                        line_no,

                    "status":
                        "missing",

                    "words":
                        words
                })

        # -------------------------------------------------
        # Insert
        # -------------------------------------------------

        elif tag == "insert":

            for a_i in range(
                a1,
                a2
            ):

                line_no += 1

                words = [

                    {
                        "status":
                            "extra",

                        "expected_word":
                            None,

                        "actual_word":
                            word
                    }

                    for word
                    in actual_lines[
                        a_i
                    ][
                        "words"
                    ]
                ]

                records.append({

                    "line_number":
                        line_no,

                    "status":
                        "extra",

                    "words":
                        words
                })

    return records


# =========================================================
# SUMMARY
# =========================================================

def summarize(
    records: List[
        Dict[str, Any]
    ]
) -> Dict[str, int]:

    stats = {

        "total_lines":
            len(records),

        "matched_lines":
            0,

        "changed_lines":
            0,

        "missing_lines":
            0,

        "extra_lines":
            0,

        "matched_words":
            0,

        "changed_words":
            0,

        "missing_words":
            0,

        "extra_words":
            0,
    }

    for record in records:

        line_key = (
            f"{record['status']}"
            "_lines"
        )

        stats[line_key] = (
            stats.get(
                line_key,
                0
            ) + 1
        )

        for word in record[
            "words"
        ]:

            word_key = (
                f"{word['status']}"
                "_words"
            )

            stats[word_key] = (
                stats.get(
                    word_key,
                    0
                ) + 1
            )

    return stats


# =========================================================
# ANNOTATION COLORS
# =========================================================

COLORS = {

    "matched":
        (0, 170, 60),

    "changed":
        (220, 30, 30),

    "missing":
        (230, 140, 0),

    "extra":
        (30, 100, 220),
}


# =========================================================
# RENDER ANNOTATED
# =========================================================

def render_annotated(
    image: Image.Image,
    records: List[
        Dict[str, Any]
    ],
    side: str
) -> Image.Image:

    img = image.copy()

    draw = ImageDraw.Draw(
        img
    )

    key = (
        f"{side}_word"
    )

    for record in records:

        for word in record[
            "words"
        ]:

            box = word.get(
                key
            )

            if not box:
                continue

            color = COLORS[
                word["status"]
            ]

            x0 = (
                box["x0"] -
                2
            )

            y0 = (
                box["y0"] -
                2
            )

            x1 = (
                box["x1"] +
                2
            )

            y1 = (
                box["y1"] +
                2
            )

            draw.rectangle(
                [
                    x0,
                    y0,
                    x1,
                    y1
                ],
                outline=color,
                width=2
            )

    return img


# =========================================================
# LEGEND
# =========================================================

def render_legend(
    width: int
) -> Image.Image:

    height = 34

    img = Image.new(
        "RGB",
        (
            width,
            height
        ),
        (
            250,
            250,
            250
        )
    )

    draw = ImageDraw.Draw(
        img
    )

    try:

        font = (
            ImageFont.truetype(
                "/usr/share/fonts/"
                "truetype/dejavu/"
                "DejaVuSansMono.ttf",
                14
            )
        )

    except Exception:

        font = (
            ImageFont.load_default()
        )

    x = 8

    values = (

        (
            "matched",
            COLORS["matched"]
        ),

        (
            "changed",
            COLORS["changed"]
        ),

        (
            "missing",
            COLORS["missing"]
        ),

        (
            "extra",
            COLORS["extra"]
        )
    )

    for label, color in values:

        draw.rectangle(
            [
                x,
                10,
                x + 16,
                24
            ],
            outline=color,
            width=3
        )

        draw.text(
            (
                x + 22,
                9
            ),
            label,
            font=font,
            fill=(0, 0, 0)
        )

        x += (
            22
            +
            len(label) * 8
            +
            24
        )

    return img


# =========================================================
# TEXT REPORT
# =========================================================

def render_text_report(
    pair_name: str,
    records: List[
        Dict[str, Any]
    ],
    stats: Dict[str, int]
) -> str:

    lines = [

        (
            "LINE-BY-LINE WORD DIFF: "
            f"{pair_name}"
        ),

        "=" * 40,

        ""
    ]

    lines.append(

        "Lines - matched: "
        f"{stats['matched_lines']}, "
        "changed: "
        f"{stats['changed_lines']}, "
        "missing: "
        f"{stats['missing_lines']}, "
        "extra: "
        f"{stats['extra_lines']}"
    )

    lines.append(

        "Words - matched: "
        f"{stats['matched_words']}, "
        "changed: "
        f"{stats['changed_words']}, "
        "missing: "
        f"{stats['missing_words']}, "
        "extra: "
        f"{stats['extra_words']}"
    )

    lines.append("")

    lines.append(
        "Note: this tool has no OCR, so it "
        "compares pixel content per detected "
        "word slot. Every CHANGED / MISSING / "
        "EXTRA word has a cropped image."
    )

    lines.append("")

    for record in records:

        lines.append(

            f"Line "
            f"{record['line_number']}: "
            f"{record['status'].upper()}"
        )

        if (
            record["status"]
            == "matched"
        ):

            lines.append(

                f"    "
                f"{len(record['words'])} "
                "word(s), all matched."
            )

        else:

            word_no = 0

            for word in record[
                "words"
            ]:

                word_no += 1

                tag = (
                    word["status"]
                    .upper()
                )

                if (
                    word["status"]
                    == "matched"
                ):

                    continue

                elif (
                    word["status"]
                    == "changed"
                ):

                    lines.append(

                        f"    word "
                        f"{word_no}: "
                        f"{tag}"
                    )

                elif (
                    word["status"]
                    == "missing"
                ):

                    lines.append(

                        f"    word "
                        f"{word_no}: "
                        f"{tag} "
                        "(present in expected, "
                        "not found in actual)"
                    )

                elif (
                    word["status"]
                    == "extra"
                ):

                    lines.append(

                        f"    word "
                        f"{word_no}: "
                        f"{tag} "
                        "(present in actual, "
                        "not in expected)"
                    )

        lines.append("")

    return "\n".join(
        lines
    )