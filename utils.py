"""Standalone document-structure analysis and chunking-method recommendation.

This module recommends "hierarchical" or "recursive" chunking. It does not
create chunks. Rule-based decisions work without an LLM. For borderline scores,
pass an optional decision_fn(doc, reason) callback returning either:
    ("hierarchical", confidence) or ("recursive", confidence)
or None. Confidence is a number from 0.0 to 1.0.

Dependencies:
    pip install pdfplumber pypdf pypandoc
For DOCX conversion, install Pandoc on your system as well.
"""

import re
from collections import Counter
from itertools import pairwise
from pathlib import Path
from typing import Callable, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import pypandoc
except ImportError:
    pypandoc = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from . import constants
    from .models import Doc, Line
except ImportError:  # supports running/importing these three files from one folder
    import constants
    from models import Doc, Line


DecisionCallback = Callable[[Doc, str], Optional[tuple[str, float]]]


def _rough_token_count(text: str) -> int:
    """Dependency-free approximation; replace with your embedding tokenizer if needed."""
    # Word/punctuation estimate, intentionally simple and deterministic.
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


def _add_token_counts(doc: Doc) -> None:
    offset = 0
    for line in doc.lines:
        line.tokens = _rough_token_count(line.text + "\n")
        line.offset = offset
        offset += line.tokens


def _is_bold_font(fontname: str) -> bool:
    name = (fontname or "").lower()
    return any(k in name for k in ("bold", "black", "heavy", "semibold", ",b"))


def _read_pdf_bookmarks(path: str) -> list[tuple[int, str]]:
    if PdfReader is None:
        return []

    def walk_outline(items, level):
        for item in items:
            if isinstance(item, list):
                yield from walk_outline(item, level + 1)
            else:
                yield level, (getattr(item, "title", "") or "").strip()

    try:
        return list(walk_outline(PdfReader(path).outline, 0))
    except Exception:
        return []


def read_pdf_document(path: str, max_pages: int = constants.MAX_PAGES) -> Doc:
    if pdfplumber is None:
        raise ImportError("PDF support requires pdfplumber. Install it with: pip install pdfplumber")
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        doc = Doc(path=path, total_pages=total, pages_read=min(total, max_pages))
        for page_no, page in enumerate(pdf.pages[:max_pages], start=1):
            try:
                extracted_lines = page.extract_text_lines(return_chars=True, strip=True)
            except TypeError:
                # Compatibility fallback for older pdfplumber versions.
                text = page.extract_text() or ""
                extracted_lines = [
                    {"text": line, "chars": []} for line in text.splitlines()
                ]

            for tl in extracted_lines:
                text = (tl.get("text") or "").strip()
                chars = [c for c in tl.get("chars", []) if not c.get("text", "").isspace()]
                if not text:
                    continue
                if chars:
                    sizes = sorted(round(c.get("size", 0) * 2) / 2 for c in chars)
                    bold = sum(_is_bold_font(c.get("fontname")) for c in chars)
                    size = sizes[len(sizes) // 2]
                    bold_ratio = bold / len(chars)
                else:
                    size, bold_ratio = 0.0, 0.0
                doc.lines.append(Line(text=text, page=page_no, size=size, bold=bold_ratio))
            try:
                page.close()
            except Exception:
                pass
    doc.bookmarks = _read_pdf_bookmarks(path)
    _add_token_counts(doc)
    return doc


def _text_to_doc(path: str, text: str) -> Doc:
    doc = Doc(
        path=path,
        total_pages=1,
        pages_read=1,
        lines=[Line(text=t.strip(), page=1) for t in text.splitlines() if t.strip()],
    )
    _add_token_counts(doc)
    return doc


def read_text_document(path: str) -> Doc:
    return _text_to_doc(path, Path(path).read_text(encoding="utf-8", errors="replace"))


def read_docx_document(path: str) -> Doc:
    if pypandoc is None:
        raise ImportError("DOCX support requires pypandoc. Install it with: pip install pypandoc")
    text = pypandoc.convert_file(
        path, "commonmark", format="docx", extra_args=["-p", "--wrap=none"]
    )
    return _text_to_doc(path, text)


def read_image_document(path: str) -> Doc:
    """Extract OCR text from scanned documents and images, then score it like text."""
    if Image is None:
        raise ImportError(
            "Image OCR requires Pillow. Install it with: pip install Pillow pytesseract"
        )
    if pytesseract is None:
        raise ImportError(
            "Image OCR requires pytesseract. Install it with: pip install Pillow pytesseract"
        )

    try:
        image = Image.open(path)
        try:
            text = pytesseract.image_to_string(image)
        finally:
            image.close()
    except Exception as exc:
        raise RuntimeError(f"OCR failed for image '{path}': {exc}") from exc

    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return _text_to_doc(path, cleaned)


def get_supported_extension(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext not in constants.SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(constants.SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported extension '{ext}'. Supported extensions: {supported}")
    return ext


def read_document(path: str, max_pages: int = constants.MAX_PAGES) -> Doc:
    ext = get_supported_extension(path)
    if ext == constants.PDF_EXTENSION:
        return read_pdf_document(path, max_pages)
    if ext == constants.DOCX_EXTENSION:
        return read_docx_document(path)
    if ext in constants.TEXT_EXTENSIONS:
        return read_text_document(path)
    if ext in constants.IMAGE_EXTENSIONS:
        return read_image_document(path)
    raise ValueError(f"Unsupported document type '{ext}'.")


def find_body_text_font_size(doc: Doc) -> float:
    counts = Counter()
    for line in doc.lines:
        if line.size:
            counts[line.size] += len(line.text)
    return counts.most_common(1)[0][0] if counts else 0.0


def find_page_headers_and_footers(doc: Doc) -> set[str]:
    if doc.pages_read < 3:
        return set()
    pages_with = Counter()
    page_keys = {(re.sub(r"\d+", "#", line.text.lower()), line.page) for line in doc.lines}
    for text_key, _ in page_keys:
        pages_with[text_key] += 1
    return {
        k for k, n in pages_with.items()
        if n >= constants.REPEATED_LINE_SHARE * doc.pages_read
    }


def count_table_of_contents_entries(doc: Doc) -> int:
    best = 0
    for i, line in enumerate(doc.lines):
        if constants.CONTENTS_RE.match(line.text):
            window = doc.lines[i + 1:i + 120]
            best = max(best, sum(1 for item in window if constants.TOC_ENTRY_RE.match(item.text)))
    return best


def find_headings_by_font(doc: Doc, body: float, skip: set[str]) -> tuple[list[int], int]:
    if not body:
        return [], 0

    def heading_style(line):
        if len(line.text) > constants.MAX_HEADING_CHARS:
            return None
        if not re.search(r"[A-Za-z]", line.text):
            return None
        if constants.TOC_ENTRY_RE.match(line.text):
            return None
        if re.sub(r"\d+", "#", line.text.lower()) in skip:
            return None
        if line.size >= body * constants.HEADING_SIZE_RATIO:
            return ("size", line.size)
        if line.bold >= constants.BOLD_RATIO and line.size >= body * 0.95:
            return ("bold", body)
        return None

    styles = [heading_style(line) for line in doc.lines]
    i = 0
    while i < len(styles):
        j = i
        while j + 1 < len(styles) and styles[i] is not None and styles[j + 1] == styles[i]:
            j += 1
        if styles[i] is not None and j - i + 1 > constants.MAX_HEADING_RUN:
            for k in range(i, j + 1):
                styles[k] = None
        i = j + 1

    used = Counter(s for s in styles if s)
    levels = {s for s, n in used.items() if n >= constants.MIN_HEADING_STYLE_LINES}
    return [i for i, s in enumerate(styles) if s in levels], len(levels)


def find_markdown_headings(doc: Doc) -> tuple[list[int], int]:
    idx, levels = [], set()
    for i, line in enumerate(doc.lines):
        match = constants.MARKDOWN_HEADING_RE.match(line.text)
        if match:
            idx.append(i)
            levels.add(len(match.group(1)))
    return idx, len(levels)


def find_numbered_headings(doc: Doc) -> list[int]:
    return [
        i for i, line in enumerate(doc.lines)
        if constants.DECIMAL_HEADING_RE.match(line.text)
        and not constants.TOC_ENTRY_RE.match(line.text)
    ]


def find_numbered_clause_levels(doc: Doc) -> tuple[list[int], bool]:
    hits = {level: [] for level in constants.CLAUSE_RES}
    for i, line in enumerate(doc.lines):
        text = line.text
        if constants.CLAUSE_RES[3].match(text):
            hits[3].append(i)
        elif constants.CLAUSE_RES[2].match(text):
            hits[2].append(i)
        elif constants.CLAUSE_RES[1].match(text):
            hits[1].append(i)

    if hits[3] and not any(
        re.match(r"^\(?(ii|iii)[.)]", doc.lines[i].text, re.IGNORECASE)
        for i in hits[3]
    ):
        hits[2] = sorted(hits[2] + hits[3])
        hits[3] = []

    present = [level for level, indexes in hits.items() if len(indexes) >= constants.MIN_CLAUSE_MARKERS]
    nested = False
    if len(present) >= 2:
        markers = sorted((i, level) for level in present for i in hits[level])
        nested = sum(1 for (_, a), (_, b) in pairwise(markers) if b > a) >= 2
    return present, nested


def add_up_rule_points(doc: Doc) -> tuple[int, list[tuple[str, int]]]:
    rules = []
    total_tokens = doc.total_tokens
    lines = doc.lines

    marks = [
        (level, title) for level, title in doc.bookmarks
        if title and not constants.FILE_NAME_RE.search(title)
    ]
    depth = len({level for level, _ in marks})
    if len(marks) >= 4 and depth >= 2:
        rules.append((f"bookmark outline {depth} levels deep with {len(marks)} entries", 3))
    elif len(marks) >= 4:
        rules.append((f"flat bookmark outline with {len(marks)} entries", 1))

    if count_table_of_contents_entries(doc) >= 3:
        rules.append(("printed table of contents", 3))

    md_idx, md_levels = find_markdown_headings(doc)
    if md_levels >= 2:
        rules.append((f"markdown headings at {md_levels} levels", 4))

    body = find_body_text_font_size(doc)
    font_idx, font_levels = find_headings_by_font(doc, body, find_page_headers_and_footers(doc))
    if font_levels >= 2:
        rules.append((f"{font_levels} heading font levels above body text", 2))
    elif font_levels == 1:
        rules.append(("one heading font level above body text", 1))

    dec_idx = find_numbered_headings(doc)
    if len(dec_idx) >= 3:
        rules.append((f"{len(dec_idx)} decimal-numbered headings (1.1 or deeper)", 3))

    clause_present, nested = find_numbered_clause_levels(doc)
    if nested:
        rules.append((f"nested numbered clauses ({len(clause_present)} levels)", 3))
    elif clause_present:
        rules.append(("numbered clauses (one level)", 2))

    heading_idx = sorted(set(font_idx) | set(md_idx) | set(dec_idx))
    n_head = len(heading_idx)
    gaps = []
    if n_head:
        bounds = [lines[i].offset for i in heading_idx] + [total_tokens]
        gaps = [b - a for a, b in pairwise(bounds)]
    avg_section = sum(gaps) / len(gaps) if gaps else 0

    if n_head >= 5 and total_tokens:
        first, last = lines[heading_idx[0]].offset, lines[heading_idx[-1]].offset
        spread = (last - first) / total_tokens
        if spread >= 0.5:
            rules.append((f"{n_head} headings spread over {spread:.0%} of the document", 2))

    if n_head >= 10 and avg_section < 40:
        rules.append((f"{n_head} headings only {avg_section:.0f} tokens apart on average (form or table labels, not sections)", -3))
    elif n_head >= 3 and 50 <= avg_section <= 1500:
        rules.append((f"sections average {avg_section:.0f} tokens", 1))

    if n_head < 3:
        rules.append(("no headings found" if not n_head else f"only {n_head} heading{'s' if n_head != 1 else ''} found", -3))

    if lines:
        prose = sum(1 for line in lines if len(line.text.split()) >= 10) / len(lines)
        if prose >= 0.6:
            rules.append((f"{prose:.0%} of lines are running prose", -2))
        form = sum(
            1 for line in lines
            if constants.FORM_FIELD_RE.match(line.text)
            and not constants.NUMBERED_ITEM_RE.match(line.text)
        ) / len(lines)
        if form >= 0.25:
            rules.append((f"{form:.0%} of lines are form fields (Label: value)", -2))

    if total_tokens < 400:
        rules.append((f"tiny document ({total_tokens} tokens)", -3))
    return sum(points for _, points in rules), rules


def explain_rule_points(points: int, rules: list[tuple[str, int]]) -> str:
    details = "; ".join(f"{description} ({points:+d})" for description, points in rules) or "no rule matched"
    return (
        f"Rule score {points} (hierarchical at >= {constants.HIERARCHICAL_AT}, "
        f"recursive at <= {constants.RECURSIVE_AT}): {details}."
    )


def choose_chunking_method(
    path: str,
    llm_config: dict | None = None,
    max_pages: int = constants.MAX_PAGES,
    decision_fn: DecisionCallback | None = None,
) -> dict:
    """Recommend a chunking method.

    `decision_fn` is only called when the rule score is ambiguous (2–5).
    It should accept `(doc, rule_reason)` and return `(method, confidence)` or None.
    Without a callback, ambiguous cases use the recursive fallback.
    """
    try:
        ext = get_supported_extension(path)
    except Exception as exc:
        return {"chunking_method": constants.FALLBACK_METHOD, "reason": str(exc)}

    try:
        doc = read_document(path, max_pages)
        points, rules = add_up_rule_points(doc)
        reason = explain_rule_points(points, rules)
        if doc.total_pages > doc.pages_read:
            reason += f" Only the first {doc.pages_read} of {doc.total_pages} pages were read."
        if ext in constants.IMAGE_EXTENSIONS:
            reason = f"OCR text extracted from image ({ext}) was scored: {reason}"
    except Exception as exc:
        return {
            "chunking_method": constants.FALLBACK_METHOD,
            "reason": f"Rule-based check failed ({type(exc).__name__}: {exc}); used {constants.FALLBACK_METHOD}.",
        }

    if points >= constants.HIERARCHICAL_AT:
        return {"chunking_method": constants.HIERARCHICAL, "reason": reason}
    if points <= constants.RECURSIVE_AT:
        return {"chunking_method": constants.RECURSIVE, "reason": reason}

    if decision_fn is None:
        return {
            "chunking_method": constants.FALLBACK_METHOD,
            "reason": f"{reason} Score is ambiguous; no decision_fn was supplied, so used {constants.FALLBACK_METHOD}.",
        }

    try:
        decision = decision_fn(doc, reason)
        if not decision:
            raise ValueError("decision_fn returned no decision")
        method, confidence = decision
        if method not in {constants.HIERARCHICAL, constants.RECURSIVE}:
            raise ValueError(f"Invalid method from decision_fn: {method!r}")
        confidence = max(0.0, min(1.0, float(confidence)))
        if confidence < constants.HIERARCHICAL_PROBABILITY:
            method = constants.RECURSIVE
        return {
            "chunking_method": method,
            "reason": f"{reason} LLM/callback decision: {method} (confidence {confidence:.2f}).",
        }
    except Exception as exc:
        return {
            "chunking_method": constants.FALLBACK_METHOD,
            "reason": f"{reason} Decision callback failed ({type(exc).__name__}: {exc}); used {constants.FALLBACK_METHOD}.",
        }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Recommend a document chunking method.")
    parser.add_argument("path", help="Path to a PDF, DOCX, TXT, MD, JPG, JPEG, or PNG file")
    parser.add_argument("--max-pages", type=int, default=constants.MAX_PAGES)
    parser.add_argument("--out", help="Optional path to write the result as JSON")
    args = parser.parse_args()

    result = choose_chunking_method(args.path, max_pages=args.max_pages)
    output = {str(Path(args.path)): result}
    print(json.dumps(output, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(output, indent=2), encoding="utf-8")


