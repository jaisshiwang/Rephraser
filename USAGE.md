# MCQ Workflow Usage Guide

This repo is a backend-only workflow for transforming multiple-choice question
banks. It can:

- import compatible external MCQ JSON into the repo's `QuestionBank` format
- rephrase existing MCQs while preserving IDs, option order, and the correct
  answer designation
- generate new grounded MCQs from supplied course material
- run through either the CLI or HTTP API

Use only course material and question-bank data that you are permitted to use.

## 1. Project Setup

From the repo root:

```bash
cd /Users/sj/Documents/Rephraser

python3 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -e .
```

Set your OpenAI credentials before running live rephrase or generate operations:

```bash
export OPENAI_API_KEY="your_key_here"
export OPENAI_MODEL="gpt-4.1-mini"
```

`OPENAI_MODEL` is optional. If omitted, the app defaults to `gpt-4.1-mini`.

## 2. Question-Bank Format

The native bank format looks like this:

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

Every question must have:

- a unique question `id`
- at least two options
- unique option IDs within the question
- exactly one option where `is_correct` is `true`

## 3. Import Compatible External MCQ JSON

If you have JSON shaped like `examtopics-downloader` output, convert it first:

```bash
mcq-workflow import-examtopics \
  --input examtopics_output.json \
  --course-id sample-cert \
  --course-title "Sample Certification" \
  --limit 10 \
  --out bank.json
```

The importer accepts records with fields such as:

- `title`
- `header`
- `content`
- `questions`
- `answer`
- `timestamp`
- `question_link`

It also accepts cached `pageProps.questions` records with fields such as:

- `question_text`
- `choices`
- `answer`
- `topic`

By default, incompatible records are skipped and counted in output metadata. To
fail on the first incompatible record:

```bash
mcq-workflow import-examtopics \
  --input examtopics_output.json \
  --course-id sample-cert \
  --course-title "Sample Certification" \
  --strict \
  --out bank.json
```

The importer only supports single-answer MCQs. Multi-answer questions are skipped
unless `--strict` is enabled, in which case the command fails.

## 4. Prepare Course Material

Rephrase and generate operations require course material for grounding. Supported
file types:

- `.pdf`
- `.txt`
- `.md`

For a quick local smoke test, create a tiny text material file:

```bash
printf "Authorized study notes for this certification. Include relevant facts here.\n" > material.txt
```

For real use, pass the actual permitted course PDFs, text files, or Markdown
files.

## 5. Rephrase A Question Bank

Create a settings file:

```bash
printf '{"rephrase_correct_answer":true,"distractor_mode":"rephrase","style":"clear and concise","preserve_difficulty":true}\n' > settings.json
```

Run the rephraser:

```bash
mcq-workflow rephrase \
  --bank bank.json \
  --material material.txt \
  --settings settings.json \
  --out rephrased.json
```

You can pass multiple materials:

```bash
mcq-workflow rephrase \
  --bank bank.json \
  --material module-1.pdf \
  --material module-2.md \
  --settings settings.json \
  --out rephrased.json
```

Rephrase settings:

```json
{
  "rephrase_correct_answer": true,
  "distractor_mode": "rephrase",
  "style": "clear and concise",
  "preserve_difficulty": true
}
```

`distractor_mode` can be:

- `keep`: keep incorrect option text exactly as-is
- `rephrase`: reword incorrect options without changing their intent
- `replace`: allow replacement distractors

The workflow always preserves:

- question IDs
- option IDs
- option order
- which option is correct

## 6. Generate New Questions

Create a generation request:

```json
{
  "course_id": "biology-101",
  "course_title": "Biology 101",
  "prompt": "Focus on applying concepts, not recall.",
  "sections": ["Cells", "Transport"],
  "count": 10,
  "style": "clear and concise",
  "difficulty": "intermediate"
}
```

Save it as `generation-request.json`, then run:

```bash
mcq-workflow generate \
  --material module-1.pdf \
  --request generation-request.json \
  --out generated.json
```

You can provide an existing bank as a style example:

```bash
mcq-workflow generate \
  --material module-1.pdf \
  --request generation-request.json \
  --bank bank.json \
  --out generated.json
```

The example bank is used only for style guidance. Generated questions get new
IDs and must match the requested sections.

## 7. Run Tests

The importer and core workflow tests can run without an OpenAI key:

```bash
PYTHONPATH=src python3 -m unittest tests.test_workflow tests.test_examtopics
```

To run the API tests too, install the full package dependencies first:

```bash
pip install -e .
PYTHONPATH=src python3 -m unittest discover -s tests
```

If FastAPI reports that multipart form support is missing:

```bash
pip install python-multipart
```

## 8. HTTP API

Start the server:

```bash
uvicorn mcq_workflow.api:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Rephrase a bank:

```bash
curl -X POST http://localhost:8000/v1/question-banks/rephrase \
  -F question_bank=@bank.json \
  -F course_material=@material.txt \
  -F 'settings={"rephrase_correct_answer":true,"distractor_mode":"rephrase","style":"clear and concise"}' \
  --output rephrased.json
```

Generate questions:

```bash
curl -X POST http://localhost:8000/v1/question-banks/generate \
  -F course_material=@material.txt \
  -F 'request={"course_id":"biology-101","course_title":"Biology 101","prompt":"Focus on applying concepts","sections":["Cells"],"count":3}' \
  --output generated.json
```

## 9. Common Issues

`OPENAI_API_KEY is not set`

Set the key in the active shell:

```bash
export OPENAI_API_KEY="your_key_here"
```

`No module named mcq_workflow`

Install the package or run with `PYTHONPATH=src`:

```bash
pip install -e .
```

`Form data requires python-multipart`

Install the multipart dependency:

```bash
pip install python-multipart
```

`no compatible single-answer MCQs found`

The importer could not find parseable single-answer MCQ records. Check that the
input JSON has option labels such as `A.`, `B.`, or a `choices` object, and an
answer like `A` or `B`.

`LLM changed option IDs`

The workflow rejected unsafe model output because the returned option IDs did not
match the input bank. This is intentional validation behavior.
