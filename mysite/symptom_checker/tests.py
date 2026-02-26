from unittest.mock import patch

from django.test import TestCase

from symptom_checker.ai_client import AIGenerationError
from symptom_checker.models import BodyArea, Condition, ConditionArticle, Doctor, Symptom
from symptom_checker.schemas import DiagnosisCondition, DiagnosisResult, QuestionItem


class ProfessionalFlowTests(TestCase):
    def setUp(self):
        area = BodyArea.objects.create(name="General")
        Symptom.objects.create(name="Nose bleeding", body_area=area)
        self.condition = Condition.objects.create(
            name="Nose Trauma",
            description="Minor trauma and irritation can cause intermittent nose bleeds.",
            urgency_level=Condition.URGENCY_CLINIC,
            specialization="ENT",
        )
        ConditionArticle.objects.create(
            condition=self.condition,
            title="Managing Nose Bleeds Safely",
            summary="First-aid steps and red-flag indicators.",
            url="https://example.com/nosebleed",
            active=True,
        )
        Doctor.objects.create(
            name="Dr. Asha Menon",
            specialization="ENT",
            city="Kochi",
            phone="9999999999",
            email="asha@example.com",
        )

    @patch("symptom_checker.engine.generate_questions")
    def test_start_creates_session_and_question_set_with_one_ai_call(self, mock_generate_questions):
        mock_generate_questions.return_value = [
            QuestionItem(id=1, text="How long has it lasted?", type="text", options=[]),
            QuestionItem(id=2, text="Any injury?", type="yesno", options=[]),
        ]

        response = self.client.post(
            "/symptoms/question/",
            data={"age": 21, "gender": "Male", "state": "Kerala", "symptom": "nose bleeding"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How long has it lasted?")

        flow = self.client.session.get("symptom_checker_flow")
        self.assertIsNotNone(flow)
        self.assertEqual(flow["ai_calls"]["questions"], 1)
        self.assertEqual(flow["ai_calls"]["diagnosis"], 0)
        self.assertEqual(len(flow["questions"]), 2)

    @patch("symptom_checker.engine.generate_questions")
    def test_start_shows_error_when_ai_question_generation_fails(self, mock_generate_questions):
        mock_generate_questions.side_effect = AIGenerationError("Gemini unavailable")

        response = self.client.post(
            "/symptoms/question/",
            data={"age": 21, "gender": "Male", "state": "Kerala", "symptom": "nose bleeding"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Live AI question generation failed")
        flow = self.client.session.get("symptom_checker_flow")
        self.assertIsNone(flow)

    @patch("symptom_checker.engine.generate_diagnosis")
    @patch("symptom_checker.engine.generate_questions")
    def test_full_flow_calls_diagnosis_once_and_renders_result(
        self, mock_generate_questions, mock_generate_diagnosis
    ):
        mock_generate_questions.return_value = [
            QuestionItem(id=1, text="How long has it lasted?", type="text", options=[]),
            QuestionItem(id=2, text="Any injury?", type="yesno", options=[]),
        ]
        mock_generate_diagnosis.return_value = DiagnosisResult(
            conditions=[
                DiagnosisCondition(
                    name="Nose Trauma",
                    likelihood="Medium",
                    reasoning="Answer pattern suggests local irritation.",
                    specialization="ENT",
                )
            ],
            urgency="Moderate",
            advice="Use local compression and consult ENT if recurring.",
        )

        self.client.post(
            "/symptoms/question/",
            data={"age": 21, "gender": "Male", "state": "Kerala", "symptom": "nose bleeding"},
        )
        self.client.post("/symptoms/question/", data={"answer": "2 days"})
        self.client.post("/symptoms/question/", data={"answer": "no"})
        result_response = self.client.get("/symptoms/result/")

        self.assertEqual(result_response.status_code, 200)
        self.assertContains(result_response, "Nose Trauma")
        self.assertContains(result_response, "Use local compression")
        self.assertContains(result_response, "Dr. Asha Menon")
        self.assertContains(result_response, "Managing Nose Bleeds Safely")

        flow = self.client.session.get("symptom_checker_flow")
        self.assertEqual(flow["ai_calls"]["questions"], 1)
        self.assertEqual(flow["ai_calls"]["diagnosis"], 1)
        self.assertEqual(mock_generate_diagnosis.call_count, 1)

        # Reopening result should not trigger another AI diagnosis call.
        self.client.get("/symptoms/result/")
        self.assertEqual(mock_generate_diagnosis.call_count, 1)
