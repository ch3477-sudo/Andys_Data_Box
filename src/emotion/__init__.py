# -*- coding: utf-8 -*-
"""
src.emotion 패키지
==================
감정 분석 및 갈등 위험도 분석 모듈.

- emotion_analyzer: 발화 단위 감정 분류 (Rule-Based + LLM)
- risk_analyzer: 대화 단위 갈등 위험도 분석 (Rule-Based + LLM)
"""

from .emotion_analyzer import (
    EMOTION_LABELS,
    EMOTION_LABEL_EN,
    EMOTION_GROUP,
    GROUP_STRATEGY,
    EmotionResult,
    DialogueEmotionResult,
    RuleBasedEmotionClassifier,
    LLMEmotionClassifier,
    analyze_emotion,
    analyze_dialogue_emotion,
    cross_validate,
)

from .risk_analyzer import (
    RISK_LEVELS,
    RISK_RECOMMENDATIONS,
    RiskResult,
    DetectedKeyword,
    RuleBasedRiskAnalyzer,
    LLMRiskAnalyzer,
    analyze_risk,
    cross_validate_risk,
    full_analysis,
)
