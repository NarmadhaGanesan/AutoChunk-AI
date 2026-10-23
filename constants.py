"""Configuration and rule patterns for document chunking recommendations."""

import re

HIERARCHICAL = "hierarchical"
RECURSIVE = "recursive"

MAX_PAGES = 30
IMAGE_DPI = 110
MAX_PDF_INPUT_BYTES = 15 * 1024 * 1024
HIERARCHICAL_PROBABILITY = 0.5

HIERARCHICAL_AT = 6
RECURSIVE_AT = 1
FALLBACK_METHOD = RECURSIVE

HEADING_SIZE_RATIO = 1.15
BOLD_RATIO = 0.9
MAX_HEADING_CHARS = 120
MIN_HEADING_STYLE_LINES = 3
MAX_HEADING_RUN = 2
REPEATED_LINE_SHARE = 0.5
MIN_CLAUSE_MARKERS = 3

PDF_EXTENSION = ".pdf"
DOCX_EXTENSION = ".docx"
TEXT_EXTENSIONS = {".md", ".txt"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_EXTENSIONS = {
    PDF_EXTENSION, DOCX_EXTENSION, *TEXT_EXTENSIONS, *IMAGE_EXTENSIONS,
}

FILE_NAME_RE = re.compile(
    r"\.(pdf|docx?|xlsx?|pptx?|txt|csv|rtf|odt|jpe?g|png|tiff?|msg|eml)\s*$",
    re.IGNORECASE,
)
CONTENTS_RE = re.compile(r"^\s*(table\s+of\s+)?contents\s*$", re.IGNORECASE)
TOC_ENTRY_RE = re.compile(r"^.*\S.*?(?:\.\s*){3,}\s*\d+\s*$|^.*\S.*?…+\s*\d+\s*$")
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
DECIMAL_HEADING_RE = re.compile(
    r"^\d{1,3}(?:\.\d{1,3})+\.?\s+[A-Z][^\n]{1," + str(MAX_HEADING_CHARS) + "}$"
)
ROMAN = r"(?:i{1,3}|iv|vi{0,3}|ix|x)"
CLAUSE_RES = {
    1: re.compile(r"^\(?\d{1,2}[.)](?!\d)\s+\S"),
    2: re.compile(r"^\(?[a-z][.)]\s+\S"),
    3: re.compile(r"^\(?" + ROMAN + r"[.)]\s+\S", re.IGNORECASE),
}
FORM_FIELD_RE = re.compile(r"^[A-Za-z][\w /&().,#'-]{0,40}:\s*\S")
NUMBERED_ITEM_RE = re.compile(
    r"^\(?(?:\d{1,3}|[a-z]|" + ROMAN + r")[.)]\s", re.IGNORECASE
)
