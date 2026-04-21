# -*- coding: utf-8 -*-
"""
app_service.py
==============
Text-only service layer for emotion/risk analysis plus RAG reply generation.
"""

from __future__ import annotations

from src.app_payload_formatter import build_text_analysis_payload
from src.emotion.llm_connector import create_gemini_caller
from src.emotion.risk_analyzer import full_analysis
from src.rag.build_rag_chain import generate_recommended_reply


def run_chat_analysis(user_input: str) -> dict:
    if not user_input or not user_input.strip():
        raise ValueError("user_input이 비어 있습니다.")

    user_input = user_input.strip()

    llm_caller = create_gemini_caller()
    emotion_risk_result = full_analysis(
        utterances=[user_input],
        dialogue_id="streamlit_chat",
        llm_caller=llm_caller,
    )

    rag_result = generate_recommended_reply(
        question=user_input,
        method="rrf",
        k=3,
    )

    return build_text_analysis_payload(
        user_input=user_input,
        emotion_risk_result=emotion_risk_result,
        rag_result=rag_result,
    )
