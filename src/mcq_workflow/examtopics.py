from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Optional

from .models import Option, Question, QuestionBank


OPTION_LABEL_RE = re.compile(
    r"^\s*(?:\*\*)?([A-Za-z])(?:\*\*)?\s*(?:[.:)\-])\s*(?:\*\*)?\s*(.+?)\s*$"
)
SUGGESTED_ANSWER_RE = re.compile(
    r"\s*(?:Suggested\s+)?Answer\s*:?\s*[A-Za-z,\s]+(?:\W*)$",
    re.IGNORECASE,
)


def question_bank_from_examtopics_json(
    value: str,
    *,
    course_id: str,
    course_title: str,
    limit: Optional[int] = None,
    strict: bool = False,
) -> QuestionBank:
    """Convert compatible examtopics-downloader JSON into a QuestionBank.

    The downloader has emitted a few related shapes over time, so this importer
    accepts both the documented question records and cached pageProps records.
    Records that are not single-answer MCQs are skipped unless strict=True.
    """
    payload = json.loads(value)
    records = _extract_records(payload)
    questions: List[Question] = []
    skipped: List[Dict[str, str]] = []

    for index, record in enumerate(records):
        if limit is not None and len(questions) >= limit:
            break
        try:
            question = _question_from_record(record, index)
        except ValueError as exc:
            if strict:
                raise ValueError(f"record {index}: {exc}") from exc
            skipped.append({"index": str(index), "reason": str(exc)})
            continue
        questions.append(_deduplicate_question_id(question, questions))

    if not questions:
        raise ValueError("no compatible single-answer MCQs found in ExamTopics JSON")

    return QuestionBank(
        course_id=course_id,
        course_title=course_title,
        questions=questions,
        metadata={
            "source": "examtopics-downloader",
            "imported_count": len(questions),
            "skipped_count": len(skipped),
            "skipped_records": skipped[:20],
        },
    )


def _extract_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        page_props = payload.get("pageProps")
        if isinstance(page_props, dict) and isinstance(page_props.get("questions"), list):
            records = page_props["questions"]
        elif isinstance(payload.get("questions"), list):
            records = payload["questions"]
        elif isinstance(payload.get("data"), list):
            records = payload["data"]
        else:
            raise ValueError("ExamTopics JSON must contain a question record array")
    else:
        raise ValueError("ExamTopics JSON must be an object or array")

    if not all(isinstance(record, dict) for record in records):
        raise ValueError("ExamTopics question records must be JSON objects")
    return records


def _question_from_record(record: Dict[str, Any], index: int) -> Question:
    answer_ids = _answer_ids(_field(record, "answer", "Answer", "answer_ET"))
    if len(answer_ids) != 1:
        raise ValueError("only single-answer MCQs are supported")
    correct_id = answer_ids[0]

    option_texts = _option_texts(record)
    if len(option_texts) < 2:
        raise ValueError("record does not contain at least two parseable options")
    if correct_id not in option_texts:
        raise ValueError(f"answer '{correct_id}' is not present in parsed options")

    question_id = _question_id(record, index)
    stem = _stem(record)
    section = _section(record)

    return Question(
        id=question_id,
        section=section,
        stem=stem,
        options=[
            Option(id=option_id, text=text, is_correct=option_id == correct_id)
            for option_id, text in option_texts.items()
        ],
        explanation=_optional_text(
            _field(record, "answer_description", "explanation", "Explanation")
        ),
        metadata={
            "source": "examtopics-downloader",
            "source_title": _optional_text(_field(record, "title", "Title")),
            "source_question_link": _optional_text(
                _field(record, "question_link", "QuestionLink", "url", "URL")
            ),
            "source_timestamp": _optional_text(
                _field(record, "timestamp", "Timestamp")
            ),
        },
    )


def _option_texts(record: Dict[str, Any]) -> Dict[str, str]:
    choices = _field(record, "choices", "Choices")
    if isinstance(choices, dict):
        parsed = {
            str(option_id).strip().upper(): _clean_text(str(text))
            for option_id, text in choices.items()
            if str(option_id).strip() and _clean_text(str(text))
        }
        return dict(sorted(parsed.items()))

    raw_questions = _field(record, "questions", "Questions")
    if not isinstance(raw_questions, list):
        return {}

    lines: List[str] = []
    for item in raw_questions:
        if not isinstance(item, str):
            continue
        lines.extend(line for line in item.splitlines() if line.strip())

    parsed: Dict[str, str] = {}
    for line in lines:
        match = OPTION_LABEL_RE.match(line)
        if not match:
            continue
        option_id = match.group(1).upper()
        text = _clean_text(match.group(2))
        if text:
            parsed[option_id] = text
    return dict(sorted(parsed.items()))


def _answer_ids(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        candidates: List[str] = []
        for item in value:
            candidates.extend(_answer_ids(item))
        return _unique(candidates)

    text = str(value).strip()
    text = re.sub(r"(?i)(suggested\s+)?answer\s*:?", "", text)
    text = re.sub(r"[^A-Za-z]", "", text)
    return _unique(letter.upper() for letter in text)


def _stem(record: Dict[str, Any]) -> str:
    for key in ("question_text", "stem", "Content", "content", "Header", "header", "Title", "title"):
        text = _optional_text(_field(record, key))
        if text and not _looks_like_media_only(text):
            stem = SUGGESTED_ANSWER_RE.sub("", text).strip()
            if stem:
                return stem
    raise ValueError("record does not contain a question stem")


def _section(record: Dict[str, Any]) -> str:
    topic = _optional_text(_field(record, "topic", "Topic", "section", "Section"))
    if topic:
        return topic if topic.lower().startswith("topic") else f"Topic {topic}"

    title = _optional_text(_field(record, "title", "Title"))
    if title:
        match = re.search(r"\btopic\s+([A-Za-z0-9_.-]+)", title, re.IGNORECASE)
        if match:
            return f"Topic {match.group(1)}"
        return title[:120]
    return "Imported"


def _question_id(record: Dict[str, Any], index: int) -> str:
    source_id = _optional_text(_field(record, "id", "ID"))
    if source_id:
        return f"examtopics-{_slug(source_id)}"

    link = _optional_text(_field(record, "question_link", "QuestionLink", "url", "URL"))
    title = _optional_text(_field(record, "title", "Title"))
    digest_source = link or title or f"record-{index}"
    digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:10]
    return f"examtopics-{digest}"


def _deduplicate_question_id(question: Question, existing: Iterable[Question]) -> Question:
    existing_ids = {item.id for item in existing}
    if question.id not in existing_ids:
        return question

    counter = 2
    while f"{question.id}-{counter}" in existing_ids:
        counter += 1
    return question.model_copy(update={"id": f"{question.id}-{counter}"})


def _field(record: Dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return None


def _optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = _clean_text(str(value))
    return text or None


def _clean_text(value: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_media_only(value: str) -> bool:
    text = value.strip()
    return bool(text) and all(
        part.startswith(("http://", "https://", "!["))
        for part in text.split()
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return slug.lower() or "question"


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    unique = []
    for value in values:
        if value and value not in seen:
            unique.append(value)
            seen.add(value)
    return unique
