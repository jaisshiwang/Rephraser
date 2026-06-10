# CourseCraft MCQ Rephraser

A dependency-free MVP for managing and rephrasing multiple-choice question banks across multiple courses. It supports per-course sections, question status tracking, JSON imports, and configurable rephrasing of question stems, correct answers, and distractors.

## Run locally

```bash
npm start
```

Open <http://localhost:3000>. Without an API key, the app uses a clearly labeled deterministic demo rephraser. For LLM-backed rephrasing:

```bash
OPENAI_API_KEY=your_key OPENAI_MODEL=gpt-4.1-mini npm start
```

## Import format

Import either an array or an object with a `questions` array. Every question must contain one correct option.

```json
{
  "questions": [{
    "section": "Cell biology",
    "stem": "What does the cell membrane do?",
    "options": [
      { "text": "Controls movement into and out of the cell", "correct": true },
      { "text": "Stores genetic material", "correct": false }
    ]
  }]
}
```

## Product direction

The current data model organizes questions by course and section so a future generation workflow can use uploaded course material and request additional questions for a chosen section. Before production use, add authentication, durable database storage, source-grounding/retrieval, and a human review/audit workflow.
