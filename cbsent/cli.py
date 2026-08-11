"""Command line interface.

    cbsent score <file>            score a document
    cbsent score -                 score text from stdin
    cbsent segment <file>          print segmented sentences
"""

import argparse
import json
import sys

from cbsent.segment import segment_sentences


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cbsent",
        description="Hawkish-dovish sentiment for central bank text",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="score a document")
    p_score.add_argument("file", help="path to a text file, or - for stdin")
    p_score.add_argument("--model-dir", default=None)
    p_score.add_argument("--json", action="store_true", help="emit full JSON")

    p_segment = sub.add_parser("segment", help="print segmented sentences")
    p_segment.add_argument("file")

    args = parser.parse_args(argv)
    text = _read(args.file)

    if args.command == "segment":
        for s in segment_sentences(text):
            print(s)
        return 0

    from cbsent.api import score

    result = score(text, model_dir=args.model_dir)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"score:  {result['score']:+.4f}")
        print(f"stance: {result['stance']}")
        print(f"sentences scored: {result['n_sentences']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
