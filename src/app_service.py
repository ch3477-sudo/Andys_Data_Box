# -*- coding: utf-8 -*-
"""
app_service.py
==============
Streamlit 앱에서 감정/위험도 분석 + RAG 추천 답변을 한 번에 호출하기 위한 통합 서비스 레이어.
"""

from __future__ import annotations

import re
from typing import Any

from src.image_input_service import extract_text_from_chat_image
from src.emotion.llm_connector import create_gemini_caller
from src.emotion.risk_analyzer import full_analysis
from src.rag.build_rag_chain import generate_recommended_reply


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _normalize_sentence(text: str) -> str:
    text = _clean_text(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -•\n\t\"'")


def _parse_section(text: str, section_name: str) -> str:
    """
    [섹션명]
    ...
    형식의 텍스트에서 해당 섹션 내용만 추출
    """
    if not text:
        return ""

    pattern = rf"\[{re.escape(section_name)}\]\s*(.*?)(?=\n\[[^\]]+\]|\Z)"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _split_lines(block_text: str) -> list[str]:
    if not block_text:
        return []

    results = []
    for line in block_text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-\*\•]\s*", "", line)
        line = re.sub(r"^\d+\.\s*", "", line)
        results.append(line)

    return results


def _is_question_sentence(text: str) -> bool:
    text = _normalize_sentence(text)
    return (
        text.endswith("?")
        or text.endswith("까?")
        or text.endswith("나요?")
        or text.endswith("을까?")
        or text.endswith("니?")
    )


def _looks_like_metadata_block(text: str) -> bool:
    """
    관계:, 상황:, 화자 감정: 같은 원문 메타데이터 덩어리인지 판별
    """
    text = _clean_text(text)
    metadata_keywords = [
        "관계:",
        "상황:",
        "화자 감정:",
        "응답 직전 문맥:",
        "추천 가능한 청자 응답 예시:",
        "응답 공감 유형:",
        "대화 종료 여부:",
        "[응답 예시",
    ]
    hit_count = sum(1 for kw in metadata_keywords if kw in text)
    if hit_count >= 2:
        return True
    if "\n" in text and hit_count >= 1:
        return True
    return False


def _is_valid_reply_candidate(text: str) -> bool:
    text = _normalize_sentence(text)
    if not text:
        return False
    if len(text) < 8:
        return False
    if len(text) > 180:
        return False
    if _looks_like_metadata_block(text):
        return False
    return True


def _extract_example_reply_candidates(text: str) -> list[str]:
    """
    텍스트 전체에서 '추천 가능한 청자 응답 예시:' 뒤 문장들을 직접 추출
    """
    if not text:
        return []

    candidates = []

    matches = re.findall(
        r"추천 가능한 청자 응답 예시:\s*(.*?)(?=\n(?:응답 공감 유형|대화 종료 여부|관계:|상황:|화자 감정:|응답 직전 문맥:)|\Z)",
        text,
        flags=re.DOTALL,
    )

    for match in matches:
        candidate = _normalize_sentence(match)
        if _is_valid_reply_candidate(candidate) and candidate not in candidates:
            candidates.append(candidate)

    return candidates


def _extract_quoted_candidates(text: str) -> list[str]:
    if not text:
        return []

    candidates = []
    quoted = re.findall(r'"([^"]{8,200})"', text)

    for q in quoted:
        q = _normalize_sentence(q)
        if _is_valid_reply_candidate(q) and q not in candidates:
            candidates.append(q)

    return candidates


def _extract_reply_candidates(result_text: str, fallback_examples: str) -> list[str]:
    """
    1) [추천 답변 1~3] 우선
    2) 전체 텍스트에서 '추천 가능한 청자 응답 예시:' 문장 직접 추출
    3) 따옴표 문장 보조 추출
    """
    candidates: list[str] = []

    # 1. [추천 답변 1], [추천 답변 2], [추천 답변 3]
    for section_name in ["추천 답변 1", "추천 답변 2", "추천 답변 3"]:
        value = _parse_section(result_text, section_name)
        value = _normalize_sentence(value)
        if _is_valid_reply_candidate(value) and value not in candidates:
            candidates.append(value)

    # 2. result_text / fallback_examples 전체에서 예시 응답 직접 추출
    for source_text in [result_text, fallback_examples]:
        extracted = _extract_example_reply_candidates(source_text)
        for item in extracted:
            if item not in candidates:
                candidates.append(item)
            if len(candidates) >= 3:
                return candidates[:3]

    # 3. 따옴표 안 문장 보조 추출
    for source_text in [result_text, fallback_examples]:
        quoted = _extract_quoted_candidates(source_text)
        for item in quoted:
            if item not in candidates:
                candidates.append(item)
            if len(candidates) >= 3:
                return candidates[:3]

    return candidates[:3]


def _parse_list_block(block_text: str, allow_questions: bool = False) -> list[str]:
    if not block_text:
        return []

    lines = _split_lines(block_text)

    if len(lines) == 1 and len(lines[0]) > 80:
        parts = re.split(r"(?<=[.!?])\s+", lines[0])
        lines = [p.strip() for p in parts if p.strip()]

    cleaned: list[str] = []
    for line in lines:
        normalized = _normalize_sentence(line)
        if not normalized:
            continue
        if _looks_like_metadata_block(normalized):
            continue
        if not allow_questions and _is_question_sentence(normalized):
            continue
        if normalized not in cleaned:
            cleaned.append(normalized)

    return cleaned[:3]


def _normalize_emotion(emotion_dict: dict) -> dict:
    dominant = _clean_text(emotion_dict.get("dominant_emotion"), "미분석")
    negative_ratio = emotion_dict.get("negative_ratio", 0.0)

    confidence = 0
    try:
        confidence = int(float(negative_ratio) * 100)
    except Exception:
        confidence = 0

    if dominant == "미분석":
        utterance_results = emotion_dict.get("utterance_results", [])
        if utterance_results and isinstance(utterance_results, list):
            first_item = utterance_results[0]
            if isinstance(first_item, dict):
                dominant = _clean_text(first_item.get("primary"), "미분석")

    return {
        "label": dominant if dominant else "미분석",
        "score": max(0, min(confidence, 100)),
        "raw": emotion_dict,
    }


def _normalize_risk(risk_dict: dict) -> dict:
    label = _clean_text(risk_dict.get("risk_label"), "미분석")
    score_raw = risk_dict.get("risk_score", 0.0)

    try:
        score = int(float(score_raw) * 100)
    except Exception:
        score = 0

    recommendation = _clean_text(risk_dict.get("recommendation"), "")

    return {
        "label": label if label else "미분석",
        "score": max(0, min(score, 100)),
        "recommendation": recommendation,
        "raw": risk_dict,
    }


def _format_risk_text(raw_risk_text: str, risk_label: str) -> str:
    """
    normal / low / high 같은 내부값이 들어와도 사용자용 문장으로 변환
    """
    raw = _normalize_sentence(raw_risk_text).lower()
    label = _normalize_sentence(risk_label)

    # 1차: raw 값 우선 해석
    if "critical" in raw or raw == "심각":
        return "감정적 대립이 매우 큰 상태라 즉각적인 설득보다 상황을 진정시키는 접근이 더 중요합니다."
    if "high" in raw or raw == "위험":
        return "현재 대화가 갈등으로 빠르게 번질 수 있어 자극적인 표현을 피하고 감정 진정이 우선입니다."
    if "normal" in raw or raw == "경고":
        return "현재 감정 충돌이 커질 가능성이 있어 표현을 부드럽게 조정하며 대화하는 것이 좋습니다."
    if "low" in raw or "safe" in raw or raw in {"안전", "주의"}:
        return "현재 갈등이 아주 심각한 수준은 아니지만, 감정이 누적되지 않도록 차분한 대화가 필요합니다."

    # 2차: 화면 라벨 기준 보정
    if label == "심각":
        return "감정적 대립이 매우 큰 상태라 즉각적인 설득보다 상황을 진정시키는 접근이 더 중요합니다."
    if label == "위험":
        return "현재 대화가 갈등으로 빠르게 번질 수 있어 자극적인 표현을 피하고 감정 진정이 우선입니다."
    if label == "경고":
        return "현재 감정 충돌이 커질 가능성이 있어 표현을 부드럽게 조정하며 대화하는 것이 좋습니다."
    if label in {"주의", "안전"}:
        return "현재 갈등이 아주 심각한 수준은 아니지만, 감정이 누적되지 않도록 차분한 대화가 필요합니다."

    return _clean_text(raw_risk_text)


def run_chat_analysis(user_input: str) -> dict:
    if not user_input or not user_input.strip():
        raise ValueError("user_input이 비어 있습니다.")

    user_input = user_input.strip()

    # 1. 감정/위험도 분석
    llm_caller = create_gemini_caller()
    emotion_risk_result = full_analysis(
        utterances=[user_input],
        dialogue_id="streamlit_chat",
        llm_caller=llm_caller,
    )

    emotion_result = emotion_risk_result.get("emotion", {})
    risk_result = emotion_risk_result.get("risk", {})

    normalized_emotion = _normalize_emotion(emotion_result)
    normalized_risk = _normalize_risk(risk_result)

    # 2. RAG 추천 답변 생성
    rag_result = generate_recommended_reply(
        question=user_input,
        method="rrf",
        k=3,
    )

    result_text = _clean_text(rag_result.get("result_text"), "")
    response_examples = _clean_text(rag_result.get("response_examples"), "")

    reply_candidates = _extract_reply_candidates(result_text, response_examples)

    summary_text = _parse_section(result_text, "상황 요약") or _clean_text(
        rag_result.get("situation_summary"), user_input
    )

    emotion_text = _parse_section(result_text, "감정") or _clean_text(
        rag_result.get("main_emotion"), ""
    )

    raw_risk_text = _parse_section(result_text, "위험도") or _clean_text(
        rag_result.get("risk_level"), ""
    )
    risk_text = _format_risk_text(raw_risk_text, normalized_risk["label"])

    avoid_text = _parse_section(result_text, "피해야 할 표현")
    alternative_text = _parse_section(result_text, "대체 표현")

    retrieved_docs = rag_result.get("retrieved_docs", [])
    retrieved_cases = []
    for doc in retrieved_docs[:3]:
        if not isinstance(doc, dict):
            continue

        situation = _clean_text(doc.get("situation"))
        speaker_emotion = _clean_text(doc.get("speaker_emotion"))
        risk_level = _clean_text(doc.get("risk_level"))

        retrieved_cases.append(
            {
                "dialogue_id": _clean_text(doc.get("dialogue_id")),
                "relation": _clean_text(doc.get("relation")),
                "situation": situation,
                "speaker_emotion": speaker_emotion,
                "risk_level": risk_level,
            }
        )

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
        "avoid_phrases": _parse_list_block(avoid_text, allow_questions=False),
        "alternative_phrases": _parse_list_block(alternative_text, allow_questions=False),
        "retrieved_cases": retrieved_cases,
        "rag_raw": rag_result,
        "emotion_risk_raw": emotion_risk_result,
    }

def run_chat_analysis_from_image_bytes(image_bytes: bytes, mime_type: str | None = None) -> dict:
    """
    이미지 업로드 입력용 분석 함수
    1) 이미지에서 대화/상황 추출
    2) 추출된 텍스트를 기존 run_chat_analysis()에 넣어 재사용
    """
    image_result = extract_text_from_chat_image(image_bytes=image_bytes, mime_type=mime_type)

    analysis_input = image_result.get("analysis_input", "").strip()
    if not analysis_input:
        raise ValueError("이미지에서 분석 가능한 텍스트를 추출하지 못했습니다.")

    result = run_chat_analysis(analysis_input)

    # 화면 표시용 추가 정보
    result["input_mode"] = "image"
    result["image_extraction"] = image_result

    # 히스토리/제목용 user_input은 상황 요약 위주로 교체
    summary = image_result.get("situation_summary", "").strip()
    if summary:
        result["user_input"] = summary
    else:
        result["user_input"] = "[이미지 업로드 대화 분석]"

    return result