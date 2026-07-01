from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .examtopics import question_bank_from_examtopics_json
from .llm import default_llm
from .materials import extract_course_material, load_material_paths
from .models import GenerateRequest, QuestionBank, RephraseSettings
from .workflow import generate_questions, rephrase_question_bank


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "import-examtopics":
        output = question_bank_from_examtopics_json(
            Path(args.input).read_text(encoding="utf-8"),
            course_id=args.course_id,
            course_title=args.course_title,
            limit=args.limit,
            strict=args.strict,
        )
    else:
        material = extract_course_material(load_material_paths(args.material))
        llm = default_llm()

    if args.command == "rephrase":
        bank = QuestionBank.model_validate_json(Path(args.bank).read_bytes())
        settings = _read_model(args.settings, RephraseSettings, "{}")
        output = rephrase_question_bank(bank, material, settings, llm)
    elif args.command == "generate":
        request = _read_model(args.request, GenerateRequest)
        example_bank = (
            QuestionBank.model_validate_json(Path(args.bank).read_bytes())
            if args.bank
            else None
        )
        output = generate_questions(request, material, llm, example_bank)

    Path(args.out).write_text(output.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transform MCQ question banks")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rephrase = subparsers.add_parser("rephrase")
    rephrase.add_argument("--bank", required=True, help="Input question-bank JSON")
    rephrase.add_argument("--material", action="append", required=True)
    rephrase.add_argument("--settings", help="Rephrase settings JSON")
    rephrase.add_argument("--out", required=True, help="Output question-bank JSON")

    generate = subparsers.add_parser("generate")
    generate.add_argument("--material", action="append", required=True)
    generate.add_argument("--request", required=True, help="Generation request JSON")
    generate.add_argument("--bank", help="Optional example question-bank JSON")
    generate.add_argument("--out", required=True, help="Output question-bank JSON")

    importer = subparsers.add_parser("import-examtopics")
    importer.add_argument("--input", required=True, help="examtopics-downloader JSON")
    importer.add_argument("--course-id", required=True)
    importer.add_argument("--course-title", required=True)
    importer.add_argument("--limit", type=int, help="Maximum compatible MCQs to import")
    importer.add_argument(
        "--strict",
        action="store_true",
        help="Fail instead of skipping incompatible records",
    )
    importer.add_argument("--out", required=True, help="Output question-bank JSON")
    return parser


def _read_model(path: Any, model: Any, default: str = "") -> Any:
    value = Path(path).read_text(encoding="utf-8") if path else default
    return model.model_validate_json(value)
