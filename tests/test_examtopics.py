import json
import unittest

from mcq_workflow.examtopics import question_bank_from_examtopics_json
from mcq_workflow.models import RephraseSettings
from mcq_workflow.workflow import rephrase_question_bank


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def generate_json(self, system_prompt, user_prompt):
        return self.responses.pop(0)


class ExamTopicsImportTests(unittest.TestCase):
    def test_imports_downloader_records_and_rephrases_small_set(self):
        payload = json.dumps(
            [
                {
                    "title": "Sample exam topic 1 question 1 discussion",
                    "header": "Sample provider exam metadata",
                    "content": "Which control limits account access to approved users?",
                    "questions": [
                        "A. Change management",
                        "B. Identity and access management",
                        "C. Capacity planning",
                        "D. Asset tagging",
                    ],
                    "answer": "B",
                    "timestamp": "Jan. 1, 2026",
                    "question_link": "https://example.test/q1",
                },
                {
                    "title": "Sample exam topic 1 question 2 discussion",
                    "header": "Sample provider exam metadata",
                    "content": "Which plan defines recovery steps after an outage?",
                    "questions": [
                        "**A:** Incident response plan",
                        "**B:** Business continuity plan",
                        "**C:** Procurement plan",
                        "**D:** Hiring plan",
                    ],
                    "answer": "B",
                    "question_link": "https://example.test/q2",
                },
            ]
        )
        bank = question_bank_from_examtopics_json(
            payload,
            course_id="sample-cert",
            course_title="Sample Certification",
            limit=2,
        )

        self.assertEqual(len(bank.questions), 2)
        self.assertEqual(bank.questions[0].section, "Topic 1")
        self.assertEqual(bank.questions[0].options[1].id, "B")
        self.assertTrue(bank.questions[0].options[1].is_correct)

        llm = FakeLLM(
            [
                {
                    "stem": "Which security control restricts account access to authorized users?",
                    "options": [
                        {"id": "A", "text": "Change control"},
                        {"id": "B", "text": "Identity and access management"},
                        {"id": "C", "text": "Capacity management"},
                        {"id": "D", "text": "Asset inventory tagging"},
                    ],
                },
                {
                    "stem": "Which document lays out recovery actions after service disruption?",
                    "options": [
                        {"id": "A", "text": "Incident response procedure"},
                        {"id": "B", "text": "Business continuity plan"},
                        {"id": "C", "text": "Purchasing plan"},
                        {"id": "D", "text": "Recruiting plan"},
                    ],
                },
            ]
        )

        rephrased = rephrase_question_bank(
            bank,
            "Authorized study notes describe access control and outage recovery.",
            RephraseSettings(),
            llm,
        )

        self.assertEqual([q.id for q in rephrased.questions], [q.id for q in bank.questions])
        self.assertEqual(
            [option.id for option in rephrased.questions[0].options],
            ["A", "B", "C", "D"],
        )
        self.assertTrue(rephrased.questions[0].options[1].is_correct)
        self.assertNotEqual(rephrased.questions[0].stem, bank.questions[0].stem)

    def test_imports_cached_page_props_records(self):
        payload = json.dumps(
            {
                "pageProps": {
                    "questions": [
                        {
                            "id": "123",
                            "topic": "Storage",
                            "question_text": "Which storage type preserves data after restart?",
                            "choices": {
                                "B": "Ephemeral memory",
                                "A": "Persistent disk",
                            },
                            "answer": "A",
                            "url": "https://example.test/q123",
                        }
                    ]
                }
            }
        )

        bank = question_bank_from_examtopics_json(
            payload,
            course_id="sample-cert",
            course_title="Sample Certification",
        )

        self.assertEqual(bank.questions[0].id, "examtopics-123")
        self.assertEqual(bank.questions[0].section, "Topic Storage")
        self.assertEqual([option.id for option in bank.questions[0].options], ["A", "B"])
        self.assertTrue(bank.questions[0].options[0].is_correct)


if __name__ == "__main__":
    unittest.main()
