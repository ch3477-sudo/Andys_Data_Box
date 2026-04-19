# -*- coding: utf-8 -*-
"""
image_input_service.py
======================
대화 캡처 이미지 1장을 받아 Gemini로
1) 대화 텍스트 추출
2) 상황 요약
3) 기존 run_chat_analysis()에 넣을 분석용 텍스트 생성
"""

from __future__ import annotations

import io
import re
from typing import Any

from PIL import Image
from google import genai

from src.emotion.llm_connector import load_secret


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _parse_section(text: str, section_name: str) -> str:
    if not text:
        return ""

    pattern = rf"\[{re.escape(section_name)}\]\s*(.*?)(?=\n\[[^\]]+\]|\Z)"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def extract_text_from_chat_image(image_bytes: bytes, mime_type: str | None = None) -> dict:
    """
    이미지에서 대화/상황을 추출하고 분석용 입력 텍스트를 생성
    """
    api_key = load_secret("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY를 찾을 수 없습니다.")

    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"이미지 파일을 열 수 없습니다: {e}")

    client = genai.Client(api_key=api_key)

    prompt = """
너는 메신저 대화 캡처 분석 보조 도우미다.

목표:
- 이미지 속 대화 내용을 가능한 자연스럽게 읽는다.
- 실제 이름을 확신하지 못하면 speaker_1, speaker_2처럼 표기한다.
- 말풍선 순서를 최대한 시간 흐름대로 정리한다.
- 추측은 최소화하고, 읽히는 범위 안에서만 정리한다.
- 출력 형식은 반드시 아래 형식을 따른다.

출력 형식:
[추출 대화]
speaker_1: ...
speaker_2: ...
speaker_1: ...

[상황 요약]
한두 문장으로 현재 갈등/대화 상황 요약

[분석용 입력]
현재 상황 요약 + 핵심 대화 내용을 합쳐서
감정/위험도/RAG 분석에 바로 넣을 수 있는 자연스러운 한국어 텍스트 3~6문장

주의:
- 불필요한 설명을 덧붙이지 말 것
- 섹션 이름을 정확히 유지할 것
- 욕설/비난/무시/회피/답장 없음 같은 갈등 신호가 있으면 분석용 입력에 반영할 것
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, image],
    )

    raw_text = _clean_text(getattr(response, "text", ""), "")
    if not raw_text:
        raise ValueError("이미지에서 텍스트를 추출하지 못했습니다.")

    extracted_dialogue = _parse_section(raw_text, "추출 대화")
    situation_summary = _parse_section(raw_text, "상황 요약")
    analysis_input = _parse_section(raw_text, "분석용 입력")

    if not analysis_input:
        parts = []
        if situation_summary:
            parts.append(f"상황 요약: {situation_summary}")
        if extracted_dialogue:
            parts.append(f"대화 내용:\n{extracted_dialogue}")
        analysis_input = "\n\n".join(parts).strip()

    if not analysis_input:
        raise ValueError("분석용 입력을 만들지 못했습니다.")

    return {
        "raw_text": raw_text,
        "extracted_dialogue": extracted_dialogue,
        "situation_summary": situation_summary,
        "analysis_input": analysis_input,
    }