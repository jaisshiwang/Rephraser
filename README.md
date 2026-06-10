# MCQ Workflow

This is a backend-only, stateless workflow:

```text
course PDFs + question-bank JSON + instruction
                    |
                    v
              LLM transformation
                    |
                    v
          validated question-bank JSON
```

It has no frontend, database, course dashboard, or review workspace. A course is
simply the files supplied with a request.

## Operations

- `rephrase`: Upload course material and an existing question bank. The output
  preserves question IDs, option IDs, option order, and the designated correct
  answer. Correct-answer text and distractor behavior are configurable.
- `generate`: Upload course material, optionally an example question bank, and a
  request describing the sections and number of questions. The output contains
  only newly generated questions.

## Question-bank JSON

```json
{
  "course_id": "biology-101",
  "course_title": "Biology 101",
  "questions": [
    {
      "id": "q-001",
      "section": "Cells",
      "stem": "What is the powerhouse of the cell?",
      "options": [
        {"id": "A", "text": "Mitochondrion", "is_correct": true},
        {"id": "B", "text": "Nucleus", "is_correct": false}
      ],
      "explanation": "Mitochondria produce most cellular ATP.",
      "metadata": {}
    }
  ],
  "metadata": {}
}
```

Each question must have unique option IDs and exactly one correct option.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-4.1-mini
```

## HTTP API

Run:

```bash
uvicorn mcq_workflow.api:app --reload
```

Rephrase a bank:

```bash
curl -X POST http://localhost:8000/v1/question-banks/rephrase \
  -F question_bank=@bank.json \
  -F course_material=@module-1.pdf \
  -F course_material=@module-2.pdf \
  -F 'settings={"rephrase_correct_answer":false,"distractor_mode":"replace","style":"academic"}' \
  --output rephrased.json
```

Generate new questions:

```bash
curl -X POST http://localhost:8000/v1/question-banks/generate \
  -F course_material=@module-1.pdf \
  -F question_bank=@bank.json \
  -F 'request={"course_id":"biology-101","course_title":"Biology 101","prompt":"Focus on applying concepts, not recall","sections":["Cells","Transport"],"count":10}' \
  --output generated.json
```

The optional bank in `generate` is used only as a style example.

## Command Line

The same workflow can run without an HTTP server:

```bash
mcq-workflow rephrase \
  --bank bank.json \
  --material module-1.pdf \
  --settings settings.json \
  --out rephrased.json

mcq-workflow generate \
  --material module-1.pdf \
  --request generation-request.json \
  --bank bank.json \
  --out generated.json
```

## Validation Guarantees

- Existing correct-answer designation is never taken from the LLM during
  rephrasing; it is copied from the input bank.
- Rephrased questions retain question IDs, option IDs, and option order.
- `keep` policies are enforced after the LLM response.
- Generated questions must use requested sections, have unique IDs, and contain
  exactly one correct option.
- Invalid LLM output fails the request instead of silently producing a bad bank.

