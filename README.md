# AutoChunk AI for RAG Systems

A small Python project that analyzes document structure and recommends either **hierarchical** or **recursive** chunking for RAG systems.

> This project recommends a chunking method. It does not split documents into chunks or implement a complete RAG pipeline.

## Files

- `utils.py` — document readers, structural signals, scoring, and the main `choose_chunking_method()` function.
- `constants.py` — scoring thresholds, supported extensions, and regular expressions.
- `models.py` — `Line`, `Doc`, and optional `ChunkingMethodDecision` data models.
- `eval_chunking_decisions.py` — lightweight validation script for checking heuristic accuracy against example labels.

## Supported formats

- PDF (`.pdf`)
- Word (`.docx`, requires Pandoc for conversion)
- Markdown (`.md`)
- Text (`.txt`)
- Images (`.jpg`, `.jpeg`, `.png`): OCR is performed when Pillow and Tesseract are installed.

## Install

Python 3.10+ is recommended.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For `.docx` support, install [Pandoc](https://pandoc.org/installing.html) too.

For OCR on images, install the system Tesseract binary:

- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- Windows: install Tesseract from the official installer and ensure it is on PATH

## Run from the command line

```bash
python utils.py path/to/document.pdf
python utils.py path/to/document.md --max-pages 10
python utils.py path/to/document.png --out result.json
```

The output contains the chosen method and an explanation:

```json
{
  "path/to/document.md": {
    "chunking_method": "recursive",
    "reason": "Rule score ..."
  }
}
```

## Use from Python

Place the three Python files in the same directory:

```python
from utils import choose_chunking_method

result = choose_chunking_method("samples/document.md")
print(result["chunking_method"])
print(result["reason"])
```

## Decision rules

- Score `>= 6`: recommend `hierarchical`.
- Score `<= 1`: recommend `recursive`.
- Score `2–5`: ambiguous; call an optional callback or default to `recursive`.

The scoring looks for PDF bookmarks, tables of contents, Markdown heading levels, font-based headings, numbered headings/clauses, heading distribution, prose-heavy lines, form fields, and very short documents.

## Optional LLM integration

The original code depended on private application modules to construct an LLM. Those imports have been removed so this version can run independently. You can supply your own model integration as a callback.

```python
def my_decision(doc, rule_reason):
    # Call your chosen LLM here.
    # Return ("hierarchical", confidence) or ("recursive", confidence).
    return ("hierarchical", 0.8)

result = choose_chunking_method("document.md", decision_fn=my_decision)
```

The callback is invoked only for ambiguous rule scores. Its `confidence` must be between 0 and 1. In this simple interface, a confidence below 0.5 resolves to recursive. The sample callback above returns a confident hierarchical decision.

## Empirical evaluation

The rule score is still a heuristic. To validate whether it predicts the best chunking method in practice, run the included evaluation utility on labeled document examples.

```bash
python eval_chunking_decisions.py --dataset examples.json
```

Example dataset format:

```json
[
  {"path": "samples/structured_report.pdf", "expected": "hierarchical"},
  {"path": "samples/notes.txt", "expected": "recursive"}
]
```

The script prints per-document predictions and overall accuracy.

## Notes and limitations

- PDF analysis is limited to the first 30 pages by default.
- Token counting is a dependency-free approximation, not the exact tokenizer used by a particular embedding model.
- OCR is available for image files only when Tesseract and the Python OCR libraries are installed.
- DOCX conversion depends on Pandoc.
- The original provider-specific LLM configuration was intentionally replaced by an optional callback because the original private `common_utils` modules were not provided.
- A higher rule score is not proof that hierarchical chunking will outperform recursive chunking; evaluate on a representative sample set before production use.

## License

No license is included. Confirm you have permission to publish the source before adding a license or publishing proprietary code.
