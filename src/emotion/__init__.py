# -*- coding: utf-8 -*-
"""
src.emotion 패키지
==================
감정 분석 및 갈등 위험도 분석 모듈 (LLM 기반).

- emotion_analyzer: 발화 단위 감정 분류 (LLM)
- risk_analyzer: 대화 단위 갈등 위험도 분석 (LLM)
"""

from .emotion_analyzer import (
    EMOTION_LABELS,
    EMOTION_LABEL_EN,
    EMOTION_GROUP,
    GROUP_STRATEGY,
    EmotionResult,
    DialogueEmotionResult,
    EmotionClassifier,
    analyze_emotion,
    analyze_dialogue_emotion,
)

from .risk_analyzer import (
    RISK_LEVELS,
    RISK_RECOMMENDATIONS,
    RiskResult,
    RiskAnalyzer,
    analyze_risk,
    full_analysis,
)


from .llm_connector import (
    DEFAULT_GEMINI_MODEL,
    GeminiConnectorError,
    GeminiFunctionCallingRouter,
    ToolDispatchResult,
    analyze_with_gemini_tools,
    create_gemini_caller,
    create_gemini_function_router,
    load_secret,
)
