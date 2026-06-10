import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from mcq_workflow.api import app


class FakeLLM:
    def generate_json(self, system_prompt, user_prompt):
        if "Generate exactly" in user_prompt:
            return {
                "questions": [
                    {
                        "id": "new-1",
                        "section": "Cells",
                        "stem": "Which organelle produces most cellular ATP?",
                        "options": [
                            {"id": "A", "text": "Mitochondrion", "is_correct": True},
                            {"id": "B", "text": "Nucleus", "is_correct": False},
                        ],
                    }
                ]
            }
        return {
            "stem": "Which organelle produces most cellular ATP?",
            "options": [
                {"id": "A", "text": "Mitochondrion"},
                {"id": "B", "text": "The nucleus"},
            ],
        }


BANK = {
    "course_id": "biology-101",
    "course_title": "Biology 101",
    "questions": [
        {
            "id": "q1",
            "section": "Cells",
            "stem": "What is the powerhouse of the cell?",
            "options": [
                {"id": "A", "text": "Mitochondrion", "is_correct": True},
                {"id": "B", "text": "Nucleus", "is_correct": False},
            ],
        }
    ],
}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_rephrase_upload_returns_json_download(self):
        with patch("mcq_workflow.api.default_llm", return_value=FakeLLM()):
            response = self.client.post(
                "/v1/question-banks/rephrase",
                files=[
                    (
                        "question_bank",
                        ("bank.json", json.dumps(BANK), "application/json"),
                    ),
                    (
                        "course_material",
                        ("course.txt", "Mitochondria produce ATP.", "text/plain"),
                    ),
                ],
                data={"settings": '{"distractor_mode":"rephrase"}'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        output = response.json()
        self.assertEqual(output["questions"][0]["id"], "q1")
        self.assertTrue(output["questions"][0]["options"][0]["is_correct"])

    def test_generate_upload_returns_requested_count(self):
        request = {
            "course_id": "biology-101",
            "course_title": "Biology 101",
            "prompt": "Write an application question",
            "sections": ["Cells"],
            "count": 1,
        }
        with patch("mcq_workflow.api.default_llm", return_value=FakeLLM()):
            response = self.client.post(
                "/v1/question-banks/generate",
                files=[
                    (
                        "course_material",
                        ("course.txt", "Mitochondria produce ATP.", "text/plain"),
                    )
                ],
                data={"request": json.dumps(request)},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["questions"]), 1)


if __name__ == "__main__":
    unittest.main()

