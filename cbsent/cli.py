"""Command line interface.

    cbsent score "Inflation remains elevated."   score text given inline
    cbsent score -f statement.txt                score a file
    cbsent score -f -                            score text from stdin
    cbsent segment -f statement.txt              print segmented sentences

Add --json for machine-readable output, --sentences to see the per
sentence breakdown behind a document score.
"""

import argparse
import json
import sys

from cbsent.segment import segment_sentences


def _read_text(args) -> str:
    if args.text:
        return " ".join(args.text)
    if args.file == "-":
        return sys.stdin.read()
    with open(args.file, encoding="utf-8") as f:
        return f.read()


def _add_input_args(parser):
    parser.add_argument("text", nargs="*",
                        help="text to score, given directly on the command line")
    parser.add_argument("-f", "--file",
                        help="read text from a file, or - for stdin")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cbsent",
        description="Hawkish-dovish sentiment for central bank text",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="score text")
    _add_input_args(p_score)
    p_score.add_argument("--model-dir", default=None)
    p_score.add_argument("--sentences", action="store_true",
                         help="show the per sentence breakdown")
    p_score.add_argument("--json", action="store_true", dest="as_json")

    p_segment = sub.add_parser("segment", help="print segmented sentences")
    _add_input_args(p_segment)

    args = parser.parse_args(argv)
    if not args.text and not args.file:
        parser.error("give text directly, or -f FILE, or -f - for stdin")

    text = _read_text(args)

    if args.command == "segment":
        for s in segment_sentences(text):
            print(s)
        return 0

    from cbsent.api import score

    result = score(text, model_dir=args.model_dir)
    if args.as_json:
        print(json.dumps(result, indent=2))
        return 0

    arrow = {"hawkish": "up", "dovish": "down", "neutral": "flat"}[result["stance"]]
    print(f"score:  {result['score']:+.4f}   ({arrow})")
    print(f"stance: {result['stance']}")
    print(f"sentences scored: {result['n_sentences']}")

    if args.sentences and result["n_sentences"] > 1:
        print()
        for r in result["sentences"]:
            label = r["stance"][:4]
            text_preview = r["text"] if len(r["text"]) <= 68 else r["text"][:65] + "..."
            print(f"  {r['score']:+.3f}  {label:<8}{text_preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
