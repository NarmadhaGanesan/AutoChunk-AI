"""CLI entrypoint for the AutoChunk package."""

from .chunking import chunk_document_json
from .scoring import choose_chunking_method

if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="AutoChunk recommendation and chunking CLI")
    parser.add_argument("path", help="Path to a PDF, DOCX, MD, TXT, or image file")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--chunk", action="store_true", help="Generate chunks instead of only the recommendation")
    parser.add_argument("--strategy", choices=["auto", "hierarchical", "recursive"], default="auto")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=50)
    parser.add_argument("--min-chunk-size", type=int, default=100)
    parser.add_argument("--max-chunk-size", type=int, default=800)
    parser.add_argument("--out", help="Optional path to write JSON output")
    args = parser.parse_args()

    if args.chunk:
        payload = {
            str(Path(args.path)): chunk_document_json(
                args.path,
                strategy=args.strategy,
                chunk_size=args.chunk_size,
                overlap=args.overlap,
                min_chunk_size=args.min_chunk_size,
                max_chunk_size=args.max_chunk_size,
                max_pages=args.max_pages,
            )
        }
    else:
        payload = {str(Path(args.path)): choose_chunking_method(args.path, max_pages=args.max_pages)}

    print(json.dumps(payload, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
