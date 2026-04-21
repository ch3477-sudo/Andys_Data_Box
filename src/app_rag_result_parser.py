# -*- coding: utf-8 -*-
"""Helpers for parsing RAG text into display-ready fragments."""

from __future__ import annotations

import re
from typing import Any


def clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def normalize_sentence(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -•\n\t\"'")


def parse_section(text: str, section_name: str) -> str:
    if not text:
        return ""

    pattern = rf"\[{re.escape(section_name)}\]\s*(.*?)(?=\n\[[^\]]+\]|\Z)"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def split_lines(block_text: str) -> list[str]:
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


def is_question_sentence(text: str) -> bool:
    text = normalize_sentence(text)
    return (
        text.endswith("?")
        or text.endswith("까?")
        or text.endswith("나요?")
        or text.endswith("을까?")
        or text.endswith("니?")
    )


def looks_like_metadata_block(text: str) -> bool:
    text = clean_text(text)
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


def is_valid_reply_candidate(text: str) -> bool:
    text = normalize_sentence(text)
    if not text:
        return False
    if len(text) < 8:
        return False
    if len(text) > 180:
        return False
    if looks_like_metadata_block(text):
        return False
    return True


def extract_example_reply_candidates(text: str) -> list[str]:
    if not text:
        return []

    candidates = []
    matches = re.findall(
        r"추천 가능한 청자 응답 예시:\s*(.*?)(?=\n(?:응답 공감 유형|대화 종료 여부|관계:|상황:|화자 감정:|응답 직전 문맥:)|\Z)",
        text,
        flags=re.DOTALL,
    )

    for match in matches:
        candidate = normalize_sentence(match)
        if is_valid_reply_candidate(candidate) and candidate not in candidates:
            candidates.append(candidate)

    return candidates


def extract_quoted_candidates(text: str) -> list[str]:
    if not text:
        return []

    candidates = []
    quoted = re.findall(r'"([^"]{8,200})"', text)

    for q in quoted:
        q = normalize_sentence(q)
        if is_valid_reply_candidate(q) and q not in candidates:
            candidates.append(q)

    return candidates


def extract_reply_candidates(result_text: str, fallback_examples: str) -> list[str]:
    candidates: list[str] = []

    for section_name in ["공감형", "완화형", "비난 회피형"]:
        value = parse_section(result_text, section_name)
        value = normalize_sentence(value)
        if is_valid_reply_candidate(value) and value not in candidates:
            candidates.append(f"[{section_name}] {value}")

    if candidates:
        return candidates[:3]

    for section_name in ["추천 답변 1", "추천 답변 2", "추천 답변 3"]:
        value = parse_section(result_text, section_name)
        value = normalize_sentence(value)
        if is_valid_reply_candidate(value) and value not in candidates:
            candidates.append(value)

    for source_text in [result_text, fallback_examples]:
        extracted = extract_example_reply_candidates(source_text)
        for item in extracted:
            if item not in candidates:
                candidates.append(item)
            if len(candidates) >= 3:
                return candidates[:3]

    for source_text in [result_text, fallback_examples]:
        quoted = extract_quoted_candidates(source_text)
        for item in quoted:
            if item not in candidates:
                candidates.append(item)
            if len(candidates) >= 3:
                return candidates[:3]

    return candidates[:3]


def parse_list_block(block_text: str, allow_questions: bool = False) -> list[str]:
    if not block_text:
        return []

    lines = split_lines(block_text)
    if len(lines) == 1 and len(lines[0]) > 80:
        parts = re.split(r"(?<=[.!?])\s+", lines[0])
        lines = [p.strip() for p in parts if p.strip()]

    cleaned: list[str] = []
    for line in lines:
        normalized = normalize_sentence(line)
        if not normalized:
            continue
        if looks_like_metadata_block(normalized):
            continue
        if not allow_questions and is_question_sentence(normalized):
            continue
        if normalized not in cleaned:
            cleaned.append(normalized)

    return cleaned[:3]
