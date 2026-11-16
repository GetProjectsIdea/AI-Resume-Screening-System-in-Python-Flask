"""Command-line version: python -m resume_screener.cli JOB.txt resumes/ [--csv out.csv]"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .extractor import SUPPORTED_EXTENSIONS, extract_text
from .scorer import screen_resumes


def load_folder(folder: Path) -> dict[str, str]:
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    return {p.name: extract_text(p) for p in files}


def write_csv(results, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Rank", "Name", "File", "Score", "Verdict", "Matched Skills", "Missing Skills"])
        for rank, r in enumerate(results, start=1):
            writer.writerow([rank, r.name, r.filename, r.score, r.verdict,
                             ", ".join(r.matched_skills), ", ".join(r.missing_skills)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rank resumes against a job description.")
    parser.add_argument("job", type=Path, help="Job description file (.txt, .pdf or .docx)")
    parser.add_argument("resumes", type=Path, help="Folder that contains the resumes")
    parser.add_argument("--csv", type=Path, help="Optional path to save the ranking as CSV")
    args = parser.parse_args(argv)

    resumes = load_folder(args.resumes)
    if not resumes:
        print(f"No PDF, DOCX or TXT resumes found in {args.resumes}", file=sys.stderr)
        return 1

    results = screen_resumes(extract_text(args.job), resumes)
    print(f"\n{'Rank':<5}{'Candidate':<22}{'Score':>7}  Verdict         Missing skills")
    print("-" * 78)
    for rank, r in enumerate(results, start=1):
        missing = ", ".join(r.missing_skills) or "-"
        print(f"{rank:<5}{r.name[:21]:<22}{r.score:>7.1f}  {r.verdict:<15} {missing}")

    if args.csv:
        write_csv(results, args.csv)
        print(f"\nSaved ranking to {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
