from __future__ import annotations

import json
import re
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError

from .llm import default_llm
from .materials import extract_course_material
from .models import GenerateRequest, QuestionBank, RephraseSettings
from .workflow import generate_questions, rephrase_question_bank


app = FastAPI(
    title="MCQ Workflow API",
    description="Backend-only PDF + JSON to JSON question-bank workflow.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/question-banks/rephrase")
async def rephrase(
    question_bank: UploadFile = File(...),
    course_material: Optional[List[UploadFile]] = File(default=None),
    settings: str = Form(default="{}"),
) -> Response:
    try:
        bank = QuestionBank.model_validate_json(await question_bank.read())
        parsed_settings = RephraseSettings.model_validate_json(settings)
        material = await _extract_uploads(course_material or [])
        output = rephrase_question_bank(bank, material, parsed_settings, default_llm())
        return _download(output, f"{bank.course_id}-rephrased.json")
    except (ValidationError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/question-banks/generate")
async def generate(
    course_material: List[UploadFile] = File(...),
    request: str = Form(...),
    question_bank: Optional[UploadFile] = File(default=None),
) -> Response:
    try:
        parsed_request = GenerateRequest.model_validate_json(request)
        example_bank = None
        if question_bank is not None:
            example_bank = QuestionBank.model_validate_json(await question_bank.read())
        material = await _extract_uploads(course_material)
        output = generate_questions(
            parsed_request, material, default_llm(), example_bank=example_bank
        )
        return _download(output, f"{parsed_request.course_id}-generated.json")
    except (ValidationError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _extract_uploads(files: List[UploadFile]) -> str:
    if not files:
        raise ValueError("at least one course material file is required")
    values = [(file.filename or "material.pdf", await file.read()) for file in files]
    return extract_course_material(values)


def _download(bank: QuestionBank, filename: str) -> Response:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "-", filename)
    return Response(
        content=bank.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )

