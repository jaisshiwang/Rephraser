from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Option(BaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    is_correct: bool


class Question(BaseModel):
    id: str = Field(min_length=1)
    section: str = Field(min_length=1)
    stem: str = Field(min_length=1)
    options: List[Option] = Field(min_length=2)
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_options(self) -> "Question":
        option_ids = [option.id for option in self.options]
        if len(set(option_ids)) != len(option_ids):
            raise ValueError("option IDs must be unique within a question")
        if sum(option.is_correct for option in self.options) != 1:
            raise ValueError("each question must have exactly one correct option")
        return self


class QuestionBank(BaseModel):
    course_id: str = Field(min_length=1)
    course_title: str = Field(min_length=1)
    questions: List[Question]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RephraseSettings(BaseModel):
    rephrase_correct_answer: bool = True
    distractor_mode: Literal["keep", "rephrase", "replace"] = "rephrase"
    style: str = "clear and concise"
    preserve_difficulty: bool = True


class GenerateRequest(BaseModel):
    course_id: str = Field(min_length=1)
    course_title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    sections: List[str] = Field(min_length=1)
    count: int = Field(gt=0, le=100)
    style: str = "clear and concise"
    difficulty: Optional[str] = None

    @model_validator(mode="after")
    def validate_sections(self) -> "GenerateRequest":
        if len(set(self.sections)) != len(self.sections):
            raise ValueError("sections must not contain duplicates")
        return self

