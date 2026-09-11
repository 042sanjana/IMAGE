"""
Streamlit frontend for the COBOL Image Diff Tool.

Shows:

- Expected image
- Actual image
- Difference image
- Annotated images
- MATCH
- CHANGED
- MISSING
- EXTRA
- Line-by-line changes
- Word/block crops
- Missing/extra images
- Existing Word report

Run:

    python -m streamlit run frontend/app.py
"""

import os

import requests
import streamlit as st


# =========================================================
# CONFIG
# =========================================================

BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "http://localhost:8000"
)


# =========================================================
# PAGE
# =========================================================

st.set_page_config(

    page_title=
        "COBOL Image Diff Tool",

    page_icon=
        "🖥️",

    layout=
        "wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>

.main-title {
    font-size: 38px;
    font-weight: 700;
}

.section-title {
    font-size: 25px;
    font-weight: 700;
    margin-top: 20px;
}

.status-match {
    padding: 12px;
    border-radius: 8px;
    background: #dff6e4;
    border: 1px solid #35a853;
    color: #176b2c;
    font-weight: 700;
}

.status-changed {
    padding: 12px;
    border-radius: 8px;
    background: #ffe2e2;
    border: 1px solid #e53935;
    color: #a40000;
    font-weight: 700;
}

.status-missing {
    padding: 12px;
    border-radius: 8px;
    background: #fff0d5;
    border: 1px solid #e58b00;
    color: #8a4d00;
    font-weight: 700;
}

.status-extra {
    padding: 12px;
    border-radius: 8px;
    background: #e1ecff;
    border: 1px solid #377dff;
    color: #164b9b;
    font-weight: 700;
}

</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# TITLE
# =========================================================

st.markdown(
    '<div class="main-title">'
    '🖥️ COBOL Image Diff Tool'
    '</div>',
    unsafe_allow_html=True
)

st.caption(
    "Expected vs Actual COBOL terminal screenshot "
    "comparison with detailed visual differences."
)


# =========================================================
# HELPERS
# =========================================================

def backend_image_url(
    path: str
):

    if not path:
        return None

    if path.startswith(
        "http://"
    ):

        return path

    if path.startswith(
        "https://"
    ):

        return path

    return (
        BACKEND_URL.rstrip("/")
        + "/"
        + path.lstrip("/")
    )


def load_image_bytes(
    path: str
):

    if not path:
        return None

    url = backend_image_url(
        path
    )

    try:

        response = requests.get(
            url,
            timeout=60
        )

        if (
            response.status_code
            == 200
        ):

            return response.content

    except requests.RequestException:
        pass

    return None


def show_image(
    path: str,
    caption: str
):

    image_bytes = load_image_bytes(
        path
    )

    if image_bytes:

        st.image(
            image_bytes,
            caption=caption,
            use_container_width=True
        )

    else:

        st.warning(
            f"{caption} could not be loaded."
        )


def status_icon(
    status: str
):

    status = (
        status
        .upper()
        .strip()
    )

    if status == "MATCH":
        return "🟢"

    if status == "MATCHED":
        return "🟢"

    if status == "CHANGED":
        return "🔴"

    if status == "MISSING":
        return "🟠"

    if status == "EXTRA":
        return "🔵"

    return "⚪"


def status_class(
    status: str
):

    status = (
        status
        .upper()
        .strip()
    )

    if status == "MATCH":
        return "status-match"

    if status == "CHANGED":
        return "status-changed"

    if status == "MISSING":
        return "status-missing"

    if status == "EXTRA":
        return "status-extra"

    return "status-match"


def show_status(
    status: str,
    text: str = None
):

    icon = status_icon(
        status
    )

    message = (
        text
        if text
        else f"{icon} {status}"
    )

    css = status_class(
        status
    )

    st.markdown(
        f'<div class="{css}">'
        f'{message}'
        f'</div>',
        unsafe_allow_html=True
    )


# =========================================================
# UPLOAD SECTION
# =========================================================

st.markdown(
    "## 1. Upload Screenshots"
)


upload_col1, upload_col2 = (
    st.columns(2)
)


# =========================================================
# ACTUAL
# =========================================================

with upload_col1:

    st.subheader(
        "🔴 ACTUAL Output"
    )

    actual_files = st.file_uploader(

        "Upload ACTUAL COBOL screenshots",

        type=[
            "png",
            "jpg",
            "jpeg",
            "bmp",
            "gif"
        ],

        accept_multiple_files=True,

        key="actual_files"
    )


# =========================================================
# EXPECTED
# =========================================================

with upload_col2:

    st.subheader(
        "🟢 EXPECTED Output"
    )

    expected_files = st.file_uploader(

        "Upload EXPECTED COBOL screenshots",

        type=[
            "png",
            "jpg",
            "jpeg",
            "bmp",
            "gif"
        ],

        accept_multiple_files=True,

        key="expected_files"
    )


# =========================================================
# FILE LIST
# =========================================================

if actual_files:

    st.info(
        f"Actual images selected: "
        f"**{len(actual_files)}**"
    )

    with st.expander(
        "View actual filenames"
    ):

        for file in actual_files:

            st.write(
                f"🔴 `{file.name}`"
            )


if expected_files:

    st.info(
        f"Expected images selected: "
        f"**{len(expected_files)}**"
    )

    with st.expander(
        "View expected filenames"
    ):

        for file in expected_files:

            st.write(
                f"🟢 `{file.name}`"
            )


st.divider()


# =========================================================
# COMPARE BUTTON
# =========================================================

valid_upload = (
    bool(actual_files)
    and
    bool(expected_files)
)


compare_button = st.button(

    "🔍 Compare Images",

    type="primary",

    disabled=
        not valid_upload,

    use_container_width=True
)


# =========================================================
# CALL BACKEND
# =========================================================

if compare_button:

    files_payload = []

    # -----------------------------------------------------
    # Actual
    # -----------------------------------------------------

    for file in actual_files:

        files_payload.append(

            (
                "actual",

                (
                    file.name,
                    file.getvalue(),
                    file.type
                    or "application/octet-stream"
                )
            )
        )

    # -----------------------------------------------------
    # Expected
    # -----------------------------------------------------

    for file in expected_files:

        files_payload.append(

            (
                "expected",

                (
                    file.name,
                    file.getvalue(),
                    file.type
                    or "application/octet-stream"
                )
            )
        )

    # -----------------------------------------------------
    # Request
    # -----------------------------------------------------

    with st.spinner(
        "Comparing COBOL screenshots..."
    ):

        try:

            response = requests.post(

                f"{BACKEND_URL}/compare",

                files=files_payload,

                timeout=300
            )

        except requests.exceptions.ConnectionError:

            st.error(
                "Could not connect to FastAPI."
            )

            st.code(
                "python -m uvicorn "
                "backend.main:app "
                "--reload "
                "--port 8000"
            )

            st.stop()

        except requests.exceptions.Timeout:

            st.error(
                "The comparison timed out."
            )

            st.stop()

    # -----------------------------------------------------
    # Error
    # -----------------------------------------------------

    if response.status_code != 200:

        st.error(
            f"FastAPI returned "
            f"HTTP {response.status_code}"
        )

        st.code(
            response.text
        )

        st.stop()

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    st.session_state[
        "comparison_result"
    ] = response.json()


# =========================================================
# NO RESULT
# =========================================================

if (
    "comparison_result"
    not in st.session_state
):

    st.info(
        "Upload EXPECTED and ACTUAL screenshots "
        "and click **Compare Images**."
    )

    st.stop()


# =========================================================
# RESULT
# =========================================================

result = st.session_state[
    "comparison_result"
]


st.success(
    result.get(
        "message",
        "Comparison completed successfully."
    )
)


# =========================================================
# SUMMARY
# =========================================================

summary = result[
    "summary"
]


st.markdown(
    "## 2. Overall Comparison Summary"
)


summary_cols = st.columns(5)


with summary_cols[0]:

    st.metric(
        "Matched",
        summary["matched"]
    )


with summary_cols[1]:

    st.metric(
        "Identical",
        summary["identical"]
    )


with summary_cols[2]:

    st.metric(
        "Changed",
        summary["changed"]
    )


with summary_cols[3]:

    st.metric(
        "Missing",
        summary["missing"]
    )


with summary_cols[4]:

    st.metric(
        "Extra",
        summary["extra"]
    )


st.divider()


# =========================================================
# WORD REPORT
# =========================================================

st.markdown(
    "## 3. Word Report"
)


report_filename = result[
    "report_filename"
]


report_url = (
    BACKEND_URL.rstrip("/")
    +
    result[
        "download_url"
    ]
)


try:

    report_response = requests.get(
        report_url,
        timeout=60
    )

    if (
        report_response.status_code
        == 200
    ):

        st.download_button(

            label=
                "⬇️ Download Word Report (.docx)",

            data=
                report_response.content,

            file_name=
                report_filename,

            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.wordprocessingml.document"
            ),

            type="primary",

            use_container_width=True
        )

    else:

        st.error(
            "Word report could not be downloaded."
        )

except requests.RequestException as exc:

    st.error(
        f"Could not connect to report endpoint: "
        f"{exc}"
    )


st.divider()


# =========================================================
# MATCHED IMAGE RESULTS
# =========================================================

st.markdown(
    "## 4. Detailed Image-by-Image Report"
)


for index, pair in enumerate(
    result["pairs"],
    start=1
):

    filename = pair[
        "filename"
    ]

    status = pair[
        "status"
    ]

    icon = status_icon(
        status
    )


    # =====================================================
    # IMAGE HEADER
    # =====================================================

    st.markdown(
        f"## {icon} {index}. `{filename}`"
    )


    # =====================================================
    # STATUS
    # =====================================================

    if status == "MATCH":

        show_status(
            "MATCH",
            "🟢 MATCH — Expected and Actual images are visually identical."
        )

    else:

        show_status(
            "CHANGED",
            "🔴 CHANGED — Differences were detected."
        )


    # =====================================================
    # METRICS
    # =====================================================

    metric_cols = st.columns(4)


    with metric_cols[0]:

        st.metric(
            "Status",
            status
        )


    with metric_cols[1]:

        st.metric(
            "Pixel Difference",
            f"{pair['percent_pixels_changed']}%"
        )


    with metric_cols[2]:

        st.metric(
            "Changed Lines",
            pair["changes_count"]
        )


    with metric_cols[3]:

        st.write(
            "**Filename**"
        )

        st.code(
            filename,
            language=None
        )


    # =====================================================
    # ORIGINAL IMAGES
    # =====================================================

    st.markdown(
        "### 4.1 Expected vs Actual"
    )


    image_col1, image_col2 = (
        st.columns(2)
    )


    with image_col1:

        st.markdown(
            "#### 🟢 EXPECTED IMAGE"
        )

        show_image(
            pair[
                "expected_image"
            ],
            "Expected screenshot"
        )


    with image_col2:

        st.markdown(
            "#### 🔴 ACTUAL IMAGE"
        )

        show_image(
            pair[
                "actual_image"
            ],
            "Actual screenshot"
        )


    # =====================================================
    # DIFFERENCE
    # =====================================================

    st.markdown(
        "### 4.2 Difference / Highlighted Image"
    )


    st.caption(
        "Red highlighted pixels indicate visual differences."
    )


    show_image(
        pair[
            "difference_image"
        ],
        "Difference image"
    )


    # =====================================================
    # ANNOTATED
    # =====================================================

    st.markdown(
        "### 4.3 Word/Block Status"
    )


    annotated_col1, annotated_col2 = (
        st.columns(2)
    )


    with annotated_col1:

        st.markdown(
            "#### EXPECTED — Annotated"
        )

        show_image(
            pair[
                "expected_annotated"
            ],
            "Expected annotated image"
        )


    with annotated_col2:

        st.markdown(
            "#### ACTUAL — Annotated"
        )

        show_image(
            pair[
                "actual_annotated"
            ],
            "Actual annotated image"
        )


    st.markdown(
        """
**Annotation legend**

🟢 Matched  
🔴 Changed  
🟠 Missing  
🔵 Extra
"""
    )


    # =====================================================
    # LINE BY LINE
    # =====================================================

    st.markdown(
        "### 4.4 Detailed Line-by-Line Changes"
    )


    lines = pair.get(
        "lines",
        []
    )


    if not lines:

        st.info(
            "No line information was generated."
        )

    else:

        for line in lines:

            line_number = line[
                "line_number"
            ]

            line_status = (
                line[
                    "status"
                ].upper()
            )

            line_icon = status_icon(
                line_status
            )


            # -------------------------------------------------
            # MATCHED LINE
            # -------------------------------------------------

            if line_status == "MATCHED":

                with st.expander(
                    f"🟢 Line {line_number} — MATCHED"
                ):

                    st.success(
                        "This line matches the expected output."
                    )

                continue


            # -------------------------------------------------
            # Changed/missing/extra line
            # -------------------------------------------------

            st.markdown(
                f"#### {line_icon} "
                f"Line {line_number} — "
                f"{line_status}"
            )


            # -------------------------------------------------
            # Full line crops
            # -------------------------------------------------

            line_col1, line_col2 = (
                st.columns(2)
            )


            with line_col1:

                st.markdown(
                    "**EXPECTED LINE**"
                )

                if line.get(
                    "expected_line"
                ):

                    show_image(
                        line[
                            "expected_line"
                        ],
                        f"Expected line {line_number}"
                    )

                else:

                    st.info(
                        "Expected line not present."
                    )


            with line_col2:

                st.markdown(
                    "**ACTUAL LINE**"
                )

                if line.get(
                    "actual_line"
                ):

                    show_image(
                        line[
                            "actual_line"
                        ],
                        f"Actual line {line_number}"
                    )

                else:

                    st.info(
                        "Actual line not present."
                    )


            # -------------------------------------------------
            # Words
            # -------------------------------------------------

            words = line.get(
                "words",
                []
            )


            changed_words = [

                word

                for word
                in words

                if word[
                    "status"
                ] != "matched"
            ]


            if not changed_words:

                st.info(
                    "No word-level changes "
                    "were detected."
                )

                continue


            st.markdown(
                "**Word / Block Changes**"
            )


            for word in changed_words:

                word_number = word[
                    "word_number"
                ]

                word_status = (
                    word[
                        "status"
                    ].upper()
                )

                word_icon = status_icon(
                    word_status
                )


                st.markdown(
                    f"##### {word_icon} "
                    f"Word {word_number} — "
                    f"{word_status}"
                )


                # =============================================
                # CHANGED
                # =============================================

                if word_status == "CHANGED":

                    expected_word_col, actual_word_col = (
                        st.columns(2)
                    )


                    with expected_word_col:

                        st.markdown(
                            "###### 🟢 EXPECTED WORD/BLOCK"
                        )

                        show_image(
                            word[
                                "expected_image"
                            ],
                            "Expected crop"
                        )


                    with actual_word_col:

                        st.markdown(
                            "###### 🔴 ACTUAL WORD/BLOCK"
                        )

                        show_image(
                            word[
                                "actual_image"
                            ],
                            "Actual crop"
                        )


                    st.error(
                        "CHANGED — The pixel content "
                        "of this detected word/block is different."
                    )


                # =============================================
                # MISSING
                # =============================================

                elif word_status == "MISSING":

                    show_status(
                        "MISSING",
                        "🟠 MISSING — Present in EXPECTED "
                        "but not detected in ACTUAL."
                    )


                    if word.get(
                        "expected_image"
                    ):

                        show_image(
                            word[
                                "expected_image"
                            ],
                            "Expected missing word/block"
                        )


                    st.info(
                        "Actual: Not present."
                    )


                # =============================================
                # EXTRA
                # =============================================

                elif word_status == "EXTRA":

                    show_status(
                        "EXTRA",
                        "🔵 EXTRA — Present in ACTUAL "
                        "but not detected in EXPECTED."
                    )


                    if word.get(
                        "actual_image"
                    ):

                        show_image(
                            word[
                                "actual_image"
                            ],
                            "Actual extra word/block"
                        )


                    st.info(
                        "Expected: Not present."
                    )


    st.divider()


# =========================================================
# MISSING ACTUAL IMAGES
# =========================================================

missing_details = result.get(
    "unmatched_expected_details",
    []
)


if missing_details:

    st.markdown(
        "## 5. MISSING Images"
    )

    st.warning(
        "These EXPECTED files do not have "
        "a matching ACTUAL file."
    )


    for item in missing_details:

        filename = item[
            "filename"
        ]

        st.markdown(
            f"### 🟠 `{filename}`"
        )


        show_status(
            "MISSING",
            "🟠 MISSING — Expected image exists, "
            "but no matching actual image was uploaded."
        )


        if item.get(
            "image"
        ):

            show_image(
                item[
                    "image"
                ],
                f"Expected image — {filename}"
            )


        st.divider()


# =========================================================
# EXTRA ACTUAL IMAGES
# =========================================================

extra_details = result.get(
    "unmatched_actual_details",
    []
)


if extra_details:

    st.markdown(
        "## 6. EXTRA Images"
    )

    st.info(
        "These ACTUAL files do not have "
        "a matching EXPECTED file."
    )


    for item in extra_details:

        filename = item[
            "filename"
        ]

        st.markdown(
            f"### 🔵 `{filename}`"
        )


        show_status(
            "EXTRA",
            "🔵 EXTRA — Actual image exists, "
            "but no matching expected image was uploaded."
        )


        if item.get(
            "image"
        ):

            show_image(
                item[
                    "image"
                ],
                f"Actual extra image — {filename}"
            )


        st.divider()


# =========================================================
# ORIGINAL FILE LIST
# =========================================================

st.markdown(
    "## 7. File Matching Information"
)


with st.expander(
    "View matched filenames"
):

    for pair in result[
        "pairs"
    ]:

        st.write(
            f"🟢 EXPECTED: "
            f"`{pair['expected_filename']}`"
        )

        st.write(
            f"🔴 ACTUAL: "
            f"`{pair['actual_filename']}`"
        )

        st.write("---")


# =========================================================
# EXPLANATION
# =========================================================

with st.expander(
    "ℹ️ How the comparison works"
):

    st.markdown(
        """
### Step 1 — Filename matching

Expected and actual files are matched using
the filename without the extension.

For example:

`PROGRAM1.png`

matches:

`PROGRAM1.PNG`

and:

`program1.jpg`

---

### Step 2 — Full image comparison

The system compares the actual screenshot
with the expected screenshot pixel-by-pixel.

The frontend displays:

- Expected image
- Actual image
- Difference image

---

### Step 3 — Line detection

The existing `word_diff.py` detects horizontal
text regions.

Each detected region becomes a line.

---

### Step 4 — Word/block detection

Within each line, pixel regions are detected.

No OCR is used.

---

### Step 5 — Word comparison

Each detected word/block is compared visually.

The result can be:

🟢 MATCHED

🔴 CHANGED

🟠 MISSING

🔵 EXTRA

---

### Step 6 — Crops

For every changed word/block, the frontend
shows:

EXPECTED:

[original crop]

ACTUAL:

[original crop]

This means the frontend displays the actual
pixels from your COBOL screenshots instead of
trying to invent OCR text.

---

### Step 7 — Word report

The existing DOCX report is generated separately
by FastAPI.

The Streamlit frontend does not modify the Word
report.
"""
    )