# -*- coding: utf-8 -*-
"""Build the app-facing payload from emotion/risk and RAG outputs."""

from __future__ import annotations

from src.app_rag_result_parser import (
    clean_text,
    extract_reply_candidates,
    normalize_sentence,
    parse_list_block,
    parse_section,
)


def normalize_emotion(emotion_dict: dict) -> dict:
    dominant = clean_text(emotion_dict.get("dominant_emotion"), "미분석")
    negative_ratio = emotion_dict.get("negative_ratio", 0.0)

    try:
        confidence = int(float(negative_ratio) * 100)
    except Exception:
        confidence = 0

    if dominant == "미분석":
        utterance_results = emotion_dict.get("utterance_results", [])
        if utterance_results and isinstance(utterance_results, list):
            first_item = utterance_results[0]
            if isinstance(first_item, dict):
                dominant = clean_text(first_item.get("primary"), "미분석")

    return {
        "label": dominant if dominant else "미분석",
        "score": max(0, min(confidence, 100)),
        "raw": emotion_dict,
    }


def normalize_risk(risk_dict: dict) -> dict:
    label = clean_text(risk_dict.get("risk_label"), "미분석")
    score_raw = risk_dict.get("risk_score", 0.0)

    try:
        score = int(float(score_raw) * 100)
    except Exception:
        score = 0

    recommendation = clean_text(risk_dict.get("recommendation"), "")

    return {
        "label": label if label else "미분석",
        "score": max(0, min(score, 100)),
        "recommendation": recommendation,
        "raw": risk_dict,
    }


def format_risk_text(raw_risk_text: str, risk_label: str) -> str:
    raw = normalize_sentence(raw_risk_text).lower()
    label = normalize_sentence(risk_label)

    if "critical" in raw or raw == "심각":
        return "감정적 대립이 매우 큰 상태라 즉각적인 설득보다 상황을 진정시키는 접근이 더 중요합니다."
    if "high" in raw or raw == "위험":
        return "현재 대화가 갈등으로 빠르게 번질 수 있어 자극적인 표현을 피하고 감정 진정이 우선입니다."
    if "normal" in raw or raw == "경고":
        return "현재 감정 충돌이 커질 가능성이 있어 표현을 부드럽게 조정하며 대화하는 것이 좋습니다."
    if "low" in raw or "safe" in raw or raw in {"안전", "주의"}:
        return "현재 갈등이 아주 심각한 수준은 아니지만, 감정이 누적되지 않도록 차분한 대화가 필요합니다."

    if label == "심각":
        return "감정적 대립이 매우 큰 상태라 즉각적인 설득보다 상황을 진정시키는 접근이 더 중요합니다."
    if label == "위험":
        return "현재 대화가 갈등으로 빠르게 번질 수 있어 자극적인 표현을 피하고 감정 진정이 우선입니다."
    if label == "경고":
        return "현재 감정 충돌이 커질 가능성이 있어 표현을 부드럽게 조정하며 대화하는 것이 좋습니다."
    if label in {"주의", "안전"}:
        return "현재 갈등이 아주 심각한 수준은 아니지만, 감정이 누적되지 않도록 차분한 대화가 필요합니다."

    return clean_text(raw_risk_text)


def format_retrieved_cases(retrieved_docs: list) -> list[dict]:
    retrieved_cases = []
    for doc in retrieved_docs[:3]:
        if not isinstance(doc, dict):
            continue

        retrieved_cases.append(
            {
                "dialogue_id": clean_text(doc.get("dialogue_id")),
                "relation": clean_text(doc.get("relation")),
                "situation": clean_text(doc.get("situation")),
                "speaker_emotion": clean_text(doc.get("speaker_emotion")),
                "risk_level": clean_text(doc.get("risk_level")),
            }
        )

    return retrieved_cases


def normalize_recommended_replies(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if not isinstance(item, dict):
            continue

        label = clean_text(item.get("label"))
        text = clean_text(item.get("text"))
        if not label or not text:
            continue

        normalized.append(
            {
                "label": label,
                "text": text,
                "source_listener_empathy": clean_text(item.get("source_listener_empathy")),
                "dialogue_id": clean_text(item.get("dialogue_id")),
            }
        )

    return normalized


def build_text_analysis_payload(
    *,
    user_input: str,
    emotion_risk_result: dict,
    rag_result: dict,
) -> dict:
    emotion_result = emotion_risk_result.get("emotion", {})
    risk_result = emotion_risk_result.get("risk", {})

    normalized_emotion = normalize_emotion(emotion_result)
    normalized_risk = normalize_risk(risk_result)

    result_text = clean_text(rag_result.get("result_text"), "")
    response_examples = clean_text(rag_result.get("response_examples"), "")
    recommended_replies = normalize_recommended_replies(
        rag_result.get("recommended_replies")
    )
    reply_candidates = extract_reply_candidates(result_text, response_examples)
    if not reply_candidates and recommended_replies:
        reply_candidates = [
            f"[{reply['label']}] {reply['text']}"
            for reply in recommended_replies
        ]

    summary_text = parse_section(result_text, "상황 요약") or clean_text(
        rag_result.get("situation_summary"), user_input
    )
    emotion_text = parse_section(result_text, "감정") or clean_text(
        rag_result.get("main_emotion"), ""
    )

    raw_risk_text = parse_section(result_text, "위험도") or clean_text(
        rag_result.get("risk_level"), ""
    )
    risk_text = format_risk_text(raw_risk_text, normalized_risk["label"])

    avoid_text = parse_section(result_text, "피해야 할 표현")
    alternative_text = parse_section(result_text, "대체 표현")
    retrieved_cases = format_retrieved_cases(rag_result.get("retrieved_docs", []))
    assistant_message = reply_candidates[0] if reply_candidates else result_text

    return {
        "user_input": user_input,
        "assistant_message": assistant_message,
        "emotion": normalized_emotion,
        "risk": normalized_risk,
        "summary_text": summary_text,
        "emotion_text": emotion_text,
        "risk_text": risk_text,
        "reply_candidates": reply_candidates,
        "recommended_replies": recommended_replies,
        "avoid_phrases": parse_list_block(avoid_text, allow_questions=False),
        "alternative_phrases": parse_list_block(alternative_text, allow_questions=False),
        "retrieved_cases": retrieved_cases,
        "rag_raw": rag_result,
        "emotion_risk_raw": emotion_risk_result,
    }
