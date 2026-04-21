# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

import pandas as pd

from src.app_payload_formatter import build_text_analysis_payload
from src.rag.build_rag_chain import (
    TARGET_RESPONSE_STYLES,
    map_listener_empathy_to_response_styles,
    select_style_labeled_response_examples,
)


class RagResponseTypeMappingTest(unittest.TestCase):
    def test_maps_existing_listener_empathy_to_target_styles(self) -> None:
        self.assertIn(
            "공감형",
            map_listener_empathy_to_response_styles("위로, 동조"),
        )
        self.assertIn(
            "완화형",
            map_listener_empathy_to_response_styles("조언, 격려"),
        )
        self.assertIn(
            "비난 회피형",
            map_listener_empathy_to_response_styles("조언, 위로"),
        )

    def test_selects_one_labeled_reply_for_each_target_style(self) -> None:
        candidate_df = pd.DataFrame(
            [
                {
                    "dialogue_id": "d1",
                    "listener_empathy": "위로, 동조",
                    "listener_response": "네가 많이 서운했겠다는 생각이 들어.",
                    "score": 5,
                },
                {
                    "dialogue_id": "d2",
                    "listener_empathy": "조언, 격려",
                    "listener_response": "조금 차분해진 뒤에 네 마음을 말해보면 좋겠어.",
                    "score": 5,
                },
                {
                    "dialogue_id": "d3",
                    "listener_empathy": "위로",
                    "listener_response": "비난하기보다 내가 느낀 감정을 먼저 말해보자.",
                    "score": 4,
                },
            ]
        )

        selected = select_style_labeled_response_examples(candidate_df)

        self.assertEqual([item["label"] for item in selected], list(TARGET_RESPONSE_STYLES))
        self.assertEqual(len({item["text"] for item in selected}), 3)

    def test_falls_back_while_preserving_target_labels(self) -> None:
        candidate_df = pd.DataFrame(
            [
                {
                    "dialogue_id": "d1",
                    "listener_empathy": "위로",
                    "listener_response": "그렇게 느낀 건 충분히 이해돼.",
                    "score": 10,
                },
                {
                    "dialogue_id": "d2",
                    "listener_empathy": "미분류",
                    "listener_response": "내 마음을 차분히 설명해볼게.",
                    "score": 8,
                },
                {
                    "dialogue_id": "d3",
                    "listener_empathy": "미분류",
                    "listener_response": "상대 탓보다 내가 바라는 점을 말해볼게.",
                    "score": 7,
                },
            ]
        )

        selected = select_style_labeled_response_examples(candidate_df)

        self.assertEqual([item["label"] for item in selected], list(TARGET_RESPONSE_STYLES))
        self.assertTrue(all(item["text"] for item in selected))

    def test_reuses_nearest_candidate_when_unique_candidates_are_insufficient(self) -> None:
        candidate_df = pd.DataFrame(
            [
                {
                    "dialogue_id": "d1",
                    "listener_empathy": "위로",
                    "listener_response": "그렇게 느낀 건 충분히 이해돼.",
                    "score": 10,
                }
            ]
        )

        selected = select_style_labeled_response_examples(candidate_df)

        self.assertEqual([item["label"] for item in selected], list(TARGET_RESPONSE_STYLES))
        self.assertEqual(len(selected), 3)
        self.assertTrue(all(item["text"] == "그렇게 느낀 건 충분히 이해돼." for item in selected))

    def test_payload_preserves_recommended_reply_labels(self) -> None:
        payload = build_text_analysis_payload(
            user_input="왜 연락 안 했어?",
            emotion_risk_result={
                "emotion": {"dominant_emotion": "분노", "negative_ratio": 0.8},
                "risk": {"risk_label": "위험", "risk_score": 0.7},
            },
            rag_result={
                "result_text": "[상황 요약]\n연락 갈등",
                "recommended_replies": [
                    {"label": "공감형", "text": "많이 서운했겠어."},
                    {"label": "완화형", "text": "조금 차분히 이야기해보자."},
                    {"label": "비난 회피형", "text": "탓하기보다 내 마음을 말해볼게."},
                ],
                "retrieved_docs": [],
            },
        )

        self.assertEqual(
            [item["label"] for item in payload["recommended_replies"]],
            list(TARGET_RESPONSE_STYLES),
        )
        self.assertEqual(payload["assistant_message"], "[공감형] 많이 서운했겠어.")
        self.assertEqual(
            payload["reply_candidates"],
            [
                "[공감형] 많이 서운했겠어.",
                "[완화형] 조금 차분히 이야기해보자.",
                "[비난 회피형] 탓하기보다 내 마음을 말해볼게.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
