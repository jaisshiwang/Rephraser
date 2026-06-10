import unittest

from mcq_workflow.models import GenerateRequest, QuestionBank, RephraseSettings
from mcq_workflow.workflow import generate_questions, rephrase_question_bank


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def generate_json(self, system_prompt, user_prompt):
        return self.responses.pop(0)


def sample_bank():
    return QuestionBank.model_validate(
        {
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
                        {"id": "C", "text": "Ribosome", "is_correct": False},
                    ],
                }
            ],
        }
    )


class RephraseWorkflowTests(unittest.TestCase):
    def test_policies_are_enforced_in_code(self):
        llm = FakeLLM(
            [
                {
                    "stem": "Which organelle supplies most cellular energy?",
                    "options": [
                        {"id": "A", "text": "Changed correct answer"},
                        {"id": "B", "text": "Changed distractor"},
                        {"id": "C", "text": "Changed distractor"},
                    ],
                }
            ]
        )
        settings = RephraseSettings(
            rephrase_correct_answer=False, distractor_mode="keep"
        )

        output = rephrase_question_bank(sample_bank(), "course text", settings, llm)

        question = output.questions[0]
        self.assertEqual(
            [option.text for option in question.options],
            ["Mitochondrion", "Nucleus", "Ribosome"],
        )
        self.assertEqual(
            [option.is_correct for option in question.options], [True, False, False]
        )
        self.assertNotEqual(question.stem, sample_bank().questions[0].stem)

    def test_rejects_changed_option_ids(self):
        llm = FakeLLM(
            [
                {
                    "stem": "A new stem",
                    "options": [
                        {"id": "A", "text": "One"},
                        {"id": "B", "text": "Two"},
                        {"id": "D", "text": "Three"},
                    ],
                }
            ]
        )

        with self.assertRaisesRegex(ValueError, "changed option IDs"):
            rephrase_question_bank(
                sample_bank(), "course text", RephraseSettings(), llm
            )


class GenerateWorkflowTests(unittest.TestCase):
    def test_generates_valid_bank(self):
        llm = FakeLLM(
            [
                {
                    "questions": [
                        {
                            "id": "new-1",
                            "section": "Cells",
                            "stem": "What structure contains genetic material?",
                            "options": [
                                {"id": "A", "text": "Nucleus", "is_correct": True},
                                {"id": "B", "text": "Golgi body", "is_correct": False},
                            ],
                        }
                    ]
                }
            ]
        )
        request = GenerateRequest(
            course_id="biology-101",
            course_title="Biology 101",
            prompt="Focus on organelles",
            sections=["Cells"],
            count=1,
        )

        output = generate_questions(request, "course text", llm)

        self.assertEqual(len(output.questions), 1)
        self.assertEqual(output.questions[0].section, "Cells")

    def test_rejects_unrequested_section(self):
        llm = FakeLLM(
            [
                {
                    "questions": [
                        {
                            "id": "new-1",
                            "section": "Genetics",
                            "stem": "A question?",
                            "options": [
                                {"id": "A", "text": "Correct", "is_correct": True},
                                {"id": "B", "text": "Wrong", "is_correct": False},
                            ],
                        }
                    ]
                }
            ]
        )
        request = GenerateRequest(
            course_id="biology-101",
            course_title="Biology 101",
            prompt="Focus on organelles",
            sections=["Cells"],
            count=1,
        )

        with self.assertRaisesRegex(ValueError, "outside the request"):
            generate_questions(request, "course text", llm)


if __name__ == "__main__":
    unittest.main()

