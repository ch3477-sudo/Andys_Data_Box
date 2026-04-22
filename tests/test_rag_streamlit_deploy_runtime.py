# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src import app_service
from src.rag import build_rag_chain as rag


class FakeDocument:
    def __init__(self, page_content: str, metadata: dict) -> None:
        self.page_content = page_content
        self.metadata = metadata


class FakeVectorStore:
    def __init__(self, docs: list[FakeDocument]) -> None:
        self.docs = docs

    def similarity_search(self, query: str, k: int = 3) -> list[FakeDocument]:
        return self.docs[:k]


class FakeChatModel:
    def invoke(self, prompt: str) -> SimpleNamespace:
        return SimpleNamespace(
            content="""
[상황 요약]
연락 문제로 서운함이 생김

[감정]
슬픔

[위험도]
주의

[공감형]
연락이 없어서 많이 서운했겠어.

[완화형]
조금 차분히 서로의 상황을 확인해보면 좋겠어.

[비난 회피형]
탓하기보다 내가 느낀 걱정을 먼저 말해볼게.

[피해야 할 표현]
- 왜 맨날 그래?

[대체 표현]
- 나는 연락이 없을 때 걱정이 커져.
"""
        )


class RagStreamlitDeployRuntimeTest(unittest.TestCase):
    def test_generate_recommended_reply_uses_pinecone_only_runtime_by_default(self) -> None:
        rag_docs = [
            FakeDocument(
                "연인 관계에서 연락 문제로 서운함을 느끼는 상황",
                {
                    "dialogue_id": "d1",
                    "relation": "연인",
                    "situation": "연락 갈등",
                    "speaker_emotion": "슬픔",
                    "risk_level": "낮음",
                },
            )
        ]
        example_docs = [
            FakeDocument(
                "네가 연락이 없어서 많이 서운했겠다는 생각이 들어.",
                {
                    "dialogue_id": "d1",
                    "relation": "연인",
                    "situation": "연락 갈등",
                    "speaker_emotion": "슬픔",
                    "listener_empathy": "위로, 동조",
                    "listener_response": "네가 연락이 없어서 많이 서운했겠다는 생각이 들어.",
                },
            ),
            FakeDocument(
                "조금 차분해진 뒤에 서로의 상황을 확인해보자.",
                {
                    "dialogue_id": "d2",
                    "listener_empathy": "조언, 격려",
                    "listener_response": "조금 차분해진 뒤에 서로의 상황을 확인해보자.",
                },
            ),
            FakeDocument(
                "탓하기보다 내 걱정을 먼저 말해볼게.",
                {
                    "dialogue_id": "d3",
                    "listener_empathy": "위로",
                    "listener_response": "탓하기보다 내 걱정을 먼저 말해볼게.",
                },
            ),
        ]

        with (
            patch.object(rag, "load_api_key", return_value="openai-key"),
            patch.object(rag, "load_dataframes") as load_dataframes,
            patch.object(rag, "load_vector_db", return_value=FakeVectorStore(rag_docs)),
            patch.object(
                rag,
                "load_example_vector_db",
                return_value=FakeVectorStore(example_docs),
            ),
            patch.object(rag, "load_llm", return_value=FakeChatModel()),
        ):
            result = rag.generate_recommended_reply("왜 연락 안 했어?", method="rrf", k=3)

        load_dataframes.assert_not_called()
        self.assertEqual(result["method"], "rrf")
        self.assertEqual(result["retrieved_docs"][0]["dialogue_id"], "d1")
        self.assertEqual(
            [item["label"] for item in result["recommended_replies"]],
            list(rag.TARGET_RESPONSE_STYLES),
        )

    def test_build_response_example_candidates_accepts_missing_response_df(self) -> None:
        example_docs = [
            FakeDocument(
                "많이 서운했겠어.",
                {
                    "dialogue_id": "d1",
                    "listener_empathy": "위로",
                    "listener_response": "많이 서운했겠어.",
                },
            )
        ]

        candidates = rag.build_response_example_candidates(
            response_df=None,
            retrieved_docs=[{"dialogue_id": "d1"}],
            emotion="슬픔",
            question="서운해",
            example_vector_db=FakeVectorStore(example_docs),
        )

        self.assertFalse(candidates.empty)
        self.assertEqual(candidates.iloc[0]["listener_response"], "많이 서운했겠어.")

    def test_bm25_requires_local_csv_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "로컬 CSV"):
            rag.retrieve_documents(
                question="서운해",
                rag_df=None,
                bm25=None,
                vector_db=FakeVectorStore([]),
                method="bm25",
                k=3,
            )

    def test_app_service_default_path_keeps_rrf_contract(self) -> None:
        with (
            patch.object(app_service, "create_gemini_caller", return_value=object()),
            patch.object(
                app_service,
                "full_analysis",
                return_value={
                    "emotion": {"dominant_emotion": "슬픔", "negative_ratio": 0.5},
                    "risk": {"risk_label": "주의", "risk_score": 0.2},
                },
            ),
            patch.object(
                app_service,
                "generate_recommended_reply",
                return_value={
                    "result_text": "[상황 요약]\n연락 갈등\n\n[공감형]\n많이 서운했겠어.",
                    "recommended_replies": [
                        {"label": "공감형", "text": "많이 서운했겠어."}
                    ],
                    "retrieved_docs": [],
                },
            ) as generate_reply,
        ):
            payload = app_service.run_chat_analysis("왜 연락 안 했어?")

        generate_reply.assert_called_once_with(
            question="왜 연락 안 했어?",
            method="rrf",
            k=3,
        )
        self.assertEqual(payload["recommended_replies"][0]["label"], "공감형")


if __name__ == "__main__":
    unittest.main()
