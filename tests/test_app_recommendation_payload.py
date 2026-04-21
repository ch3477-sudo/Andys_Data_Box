# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from src.app_payload_formatter import build_text_analysis_payload
from src.app_rag_result_parser import extract_reply_candidates


class AppRecommendationPayloadTest(unittest.TestCase):
    def test_extracts_labeled_llm_recommendation_sections(self) -> None:
        result_text = """
[상황 요약]
연락 문제로 서운함이 생김

[공감형]
네가 연락이 없어서 많이 서운했겠다.

[완화형]
조금 진정한 뒤에 내가 바랐던 점을 차분히 말해보자.

[비난 회피형]
너를 탓하려는 건 아니고, 나는 연락이 없을 때 걱정이 커졌어.
"""

        self.assertEqual(
            extract_reply_candidates(result_text, ""),
            [
                "[공감형] 네가 연락이 없어서 많이 서운했겠다.",
                "[완화형] 조금 진정한 뒤에 내가 바랐던 점을 차분히 말해보자.",
                "[비난 회피형] 너를 탓하려는 건 아니고, 나는 연락이 없을 때 걱정이 커졌어.",
            ],
        )

    def test_payload_prefers_llm_sections_over_rag_evidence(self) -> None:
        payload = build_text_analysis_payload(
            user_input="왜 연락 안 했어?",
            emotion_risk_result={
                "emotion": {"dominant_emotion": "슬픔", "negative_ratio": 0.6},
                "risk": {"risk_label": "주의", "risk_score": 0.3},
            },
            rag_result={
                "result_text": """
[상황 요약]
연락 문제로 서운함이 생김

[공감형]
연락이 없어서 많이 서운했겠어.

[완화형]
조금 차분히 서로의 상황을 확인해보면 좋겠어.

[비난 회피형]
탓하기보다 내가 느낀 걱정을 먼저 말해볼게.
""",
                "recommended_replies": [
                    {"label": "공감형", "text": "raw rag empathy"},
                    {"label": "완화형", "text": "raw rag softening"},
                    {"label": "비난 회피형", "text": "raw rag avoid blame"},
                ],
                "retrieved_docs": [],
            },
        )

        self.assertEqual(
            payload["reply_candidates"],
            [
                "[공감형] 연락이 없어서 많이 서운했겠어.",
                "[완화형] 조금 차분히 서로의 상황을 확인해보면 좋겠어.",
                "[비난 회피형] 탓하기보다 내가 느낀 걱정을 먼저 말해볼게.",
            ],
        )
        self.assertEqual(payload["assistant_message"], "[공감형] 연락이 없어서 많이 서운했겠어.")
        self.assertEqual(payload["recommended_replies"][0]["text"], "raw rag empathy")


if __name__ == "__main__":
    unittest.main()
