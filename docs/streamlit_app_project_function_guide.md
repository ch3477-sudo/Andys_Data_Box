# Streamlit App 프로젝트 함수 사용 가이드

## 목적

`app/streamlit_app.py`를 기준으로 현재 프로젝트에 이미 있는 기능을 어떻게 연결할지 정리한다.

현재 `streamlit_app.py`는 UI 목업에 가깝다.
감정 분석, 위험도 분석, 추천 답변, 대화 히스토리 값이 대부분 고정값이다.
실제 서비스 동작을 위해서는 `src/rag`, `src/emotion` 쪽 함수를 연결해야 한다.

---

## 1. 현재 `streamlit_app.py` 구조

파일:

```text
app/streamlit_app.py
```

현재 함수:

| 함수 | 역할 | 현재 상태 |
|---|---|---|
| `apply_custom_css()` | Streamlit 화면 CSS 적용 | 사용 중 |
| `render_analysis_card(title, emoji, label, score, color)` | 감정/위험도 카드 렌더링 | 고정값 표시 |
| `render_history_item(icon, title, time, preview, is_active=False)` | 히스토리 항목 렌더링 | 고정값 표시 |
| `main()` | 전체 Streamlit 화면 구성 | 분석 로직 미연결 |

현재 고정값 예시:

```python
render_analysis_card("감정 분석", "😡", "분노", 92, "#5C7CFA")
render_analysis_card("위험도 분석", "⏱️", "높음", 88, "#E74C3C")
```

현재 추천 답변 고정값:

```python
recs = [
    "지금 화가 많이 난 것 같아. 무슨 일이 있었는지 이야기해줄래?",
    "내 마음이 이해돼. 잠시 숨을 고르고 천천히 이야기해보자.",
    "그런 일이 있어서 속상했겠네. 내가 들어줄게.",
]
```

---

## 2. Streamlit 앱에서 우선 연결할 기능

우선순위:

1. 사용자 입력 저장
2. 대화 발화 리스트 생성
3. 감정 분석
4. 위험도 분석
5. RAG 추천 답변 생성
6. 분석 카드 동적 표시
7. 추천 답변 동적 표시
8. 최근 대화 히스토리 표시

---

## 3. API key 로딩

### 사용할 파일

```text
src/rag/api_key_loader.py
```

### 사용할 함수

```python
from src.rag.api_key_loader import load_api_key
```

### 역할

`OPENAI_API_KEY`를 다음 순서로 가져온다.

1. `.streamlit/secrets.toml`
2. `data/.env`
3. 루트 `.env`

### 예시

```python
from src.rag.api_key_loader import load_api_key

openai_api_key = load_api_key("OPENAI_API_KEY")
```

`build_rag_chain.generate_recommended_reply()` 내부에서도 `load_api_key()`를 사용한다.
따라서 Streamlit app에서 RAG 추천만 사용할 경우 직접 호출이 필수는 아니다.

---

## 4. RAG 추천 답변 생성

### 사용할 파일

```text
src/rag/build_rag_chain.py
```

### 핵심 함수

```python
from src.rag.build_rag_chain import generate_recommended_reply
```

### 함수 역할

사용자 질문을 받아 다음 결과를 반환한다.

```python
{
    "question": 질문,
    "method": 검색방식,
    "retrieved_docs": 검색문서목록,
    "situation_summary": 상황요약,
    "main_emotion": 주요감정,
    "risk_level": 위험도,
    "response_examples": 추천 예시,
    "result_text": 최종추천답변,
}
```

### 기본 사용 예시

```python
from src.rag.build_rag_chain import generate_recommended_reply

rag_result = generate_recommended_reply(
    question="남자친구가 내 말을 제대로 안 들어줘서 서운해. 뭐라고 보내면 좋을까?",
    method="rrf",
    k=3,
)

recommended_text = rag_result["result_text"]
retrieved_docs = rag_result["retrieved_docs"]
situation_summary = rag_result["situation_summary"]
main_emotion = rag_result["main_emotion"]
risk_level = rag_result["risk_level"]
```

### Streamlit 연결 예시

```python
if prompt := st.chat_input("메시지를 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("추천 답변 생성 중..."):
        rag_result = generate_recommended_reply(prompt, method="rrf", k=3)

    st.session_state.latest_rag_result = rag_result
    st.session_state.messages.append({
        "role": "assistant",
        "avatar": "🍴",
        "content": rag_result["result_text"],
    })
    st.rerun()
```

---

## 5. 감정 분석

### 사용할 파일

```text
src/emotion/emotion_analyzer.py
src/emotion/llm_connector.py
```

### 사용할 함수

```python
from src.emotion import create_gemini_caller
from src.emotion import analyze_emotion, analyze_dialogue_emotion
```

### 단일 발화 분석 예시

```python
from src.emotion import create_gemini_caller, analyze_emotion

llm_caller = create_gemini_caller()

emotion_result = analyze_emotion(
    "너 왜 또 늦었어?",
    llm_caller=llm_caller,
)

primary = emotion_result.primary
confidence = emotion_result.confidence_percent
strategy = emotion_result.strategy
reasoning = emotion_result.reasoning
```

### 대화 전체 감정 분석 예시

```python
from src.emotion import create_gemini_caller, analyze_dialogue_emotion

llm_caller = create_gemini_caller()

utterances = [
    "너 왜 또 늦었어?",
    "미안해. 일이 늦게 끝났어.",
    "항상 이런 식이잖아.",
]

emotion_result = analyze_dialogue_emotion(
    utterances,
    dialogue_id="chat_001",
    llm_caller=llm_caller,
)

emotion_sequence = emotion_result.emotion_sequence
dominant_emotion = emotion_result.dominant_emotion
negative_ratio = emotion_result.negative_ratio_percent
volatility = emotion_result.emotion_volatility_percent
```

---

## 6. 위험도 분석

### 사용할 파일

```text
src/emotion/risk_analyzer.py
```

### 사용할 함수

```python
from src.emotion import analyze_risk, full_analysis
```

### 위험도만 분석

```python
from src.emotion import create_gemini_caller, analyze_risk

llm_caller = create_gemini_caller()

risk_result = analyze_risk(
    [
        "너 왜 또 늦었어?",
        "미안해. 일이 늦게 끝났어.",
    ],
    dialogue_id="chat_001",
    llm_caller=llm_caller,
)

risk_label = risk_result.risk_label
risk_level = risk_result.risk_level
risk_score = risk_result.risk_score_percent
recommendation = risk_result.recommendation
```

### 감정 + 위험도 통합 분석

Streamlit 앱에서는 이 방식이 가장 단순하다.

```python
from src.emotion import create_gemini_caller, full_analysis

llm_caller = create_gemini_caller()

analysis = full_analysis(
    [
        "너 왜 또 늦었어?",
        "미안해. 일이 늦게 끝났어.",
        "항상 이런 식이잖아.",
    ],
    dialogue_id="chat_001",
    llm_caller=llm_caller,
)

emotion = analysis["emotion"]
risk = analysis["risk"]
```

반환값 사용 예:

```python
emotion_label = emotion["dominant_emotion"]
emotion_score = emotion["negative_ratio_percent"]
risk_label = risk["risk_label"]
risk_score = risk["risk_score_percent"]
```

---

## 7. Gemini Function Calling Router

### 사용할 파일

```text
src/emotion/llm_connector.py
```

### 사용할 함수

```python
from src.emotion import create_gemini_function_router
```

### 역할

Gemini가 아래 도구 중 하나를 선택해 실행하도록 구성한다.

| tool name | 연결 함수 |
|---|---|
| `analyze_single_emotion` | `analyze_emotion()` |
| `analyze_dialogue_emotion` | `analyze_dialogue_emotion()` |
| `analyze_dialogue_risk` | `analyze_risk()` |
| `full_dialogue_analysis` | `full_analysis()` |

### 사용 예시

```python
from src.emotion import create_gemini_function_router

router = create_gemini_function_router()

response = router.route(
    "다음 대화의 감정 흐름과 갈등 위험도를 분석해줘: "
    "['너 왜 또 늦었어?', '미안해. 일이 늦게 끝났어.']"
)
```

### Streamlit에서 권장 사용 위치

- 일반 추천 답변: `generate_recommended_reply()` 우선
- 감정/위험도 카드: `full_analysis()` 우선
- 사용자가 자유 형식으로 “분석해줘”라고 요청하는 기능: `create_gemini_function_router()` 사용 가능

---

## 8. `streamlit_app.py`에서 추가하면 좋은 내부 함수

현재 `streamlit_app.py`는 모든 로직이 `main()` 안에 몰려 있다.
아래 함수를 app 내부에 추가하면 연결이 쉬워진다.

### 8.1 프로젝트 import 경로 설정

`app/streamlit_app.py`는 `app/` 폴더에 있으므로 `src` import를 위해 프로젝트 루트를 path에 추가한다.

```python
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
```

### 8.2 대화 발화 리스트 생성

```python
def build_utterances_from_messages(messages: list[dict]) -> list[str]:
    return [
        message["content"]
        for message in messages
        if message.get("role") in {"user", "assistant"}
        and message.get("content")
    ]
```

### 8.3 RAG 추천 실행

```python
def run_rag_recommendation(prompt: str) -> dict:
    from src.rag.build_rag_chain import generate_recommended_reply

    return generate_recommended_reply(
        question=prompt,
        method="rrf",
        k=3,
    )
```

### 8.4 감정/위험도 통합 분석 실행

```python
def run_emotion_risk_analysis(utterances: list[str]) -> dict:
    from src.emotion import create_gemini_caller, full_analysis

    llm_caller = create_gemini_caller()
    return full_analysis(
        utterances,
        dialogue_id="streamlit_current_chat",
        llm_caller=llm_caller,
    )
```

### 8.5 분석 카드 데이터 변환

```python
def build_analysis_cards(analysis: dict) -> dict:
    emotion = analysis["emotion"]
    risk = analysis["risk"]

    return {
        "emotion": {
            "emoji": "😡" if emotion["dominant_group"] == "negative" else "🙂",
            "label": emotion["dominant_emotion"],
            "score": emotion["negative_ratio_percent"],
            "color": "#5C7CFA",
        },
        "risk": {
            "emoji": "⏱️",
            "label": risk["risk_label"],
            "score": risk["risk_score_percent"],
            "color": "#E74C3C" if risk["risk_score_percent"] >= 60 else "#37B24D",
        },
    }
```

### 8.6 추천 답변 리스트 추출

`generate_recommended_reply()`의 `result_text`가 여러 문장을 포함할 수 있으므로 우선 단일 추천으로 표시한다.
추후 파싱 규칙을 추가한다.

```python
def build_recommendations(rag_result: dict) -> list[str]:
    result_text = rag_result.get("result_text", "")
    if not result_text:
        return []
    return [result_text]
```

---

## 9. Streamlit 통합 예시

아래는 현재 `main()`의 `st.chat_input()` 처리부를 대체할 수 있는 형태다.

```python
if prompt := st.chat_input("메시지를 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("AI 분석 및 추천 답변 생성 중..."):
        rag_result = run_rag_recommendation(prompt)
        utterances = build_utterances_from_messages(st.session_state.messages)
        analysis = run_emotion_risk_analysis(utterances)

    st.session_state.latest_rag_result = rag_result
    st.session_state.latest_analysis = analysis
    st.session_state.messages.append({
        "role": "assistant",
        "avatar": "🍴",
        "content": rag_result["result_text"],
    })
    st.rerun()
```

오른쪽 분석 카드 렌더링 예:

```python
analysis = st.session_state.get("latest_analysis")

if analysis:
    cards = build_analysis_cards(analysis)
    with card_l:
        render_analysis_card(
            "감정 분석",
            cards["emotion"]["emoji"],
            cards["emotion"]["label"],
            cards["emotion"]["score"],
            cards["emotion"]["color"],
        )
    with card_r:
        render_analysis_card(
            "위험도 분석",
            cards["risk"]["emoji"],
            cards["risk"]["label"],
            cards["risk"]["score"],
            cards["risk"]["color"],
        )
else:
    with card_l:
        render_analysis_card("감정 분석", "💬", "대기", 0, "#ADB5BD")
    with card_r:
        render_analysis_card("위험도 분석", "⏱️", "대기", 0, "#ADB5BD")
```

추천 답변 렌더링 예:

```python
rag_result = st.session_state.get("latest_rag_result")
recommendations = build_recommendations(rag_result) if rag_result else []

if recommendations:
    for index, text in enumerate(recommendations, 1):
        st.markdown(
            f'<div class="list-item"><div class="item-icon">{index}</div>'
            f'<div class="item-content">{text}</div>'
            f'<div style="color:#ccc;">❐</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.info("메시지를 입력하면 추천 답변이 표시됩니다.")
```

---

## 10. 기능별 사용 판단표

| Streamlit 기능 | 사용할 프로젝트 함수 | 비고 |
|---|---|---|
| API key 확인 | `src.rag.api_key_loader.load_api_key()` | RAG용 OpenAI key |
| 추천 답변 생성 | `src.rag.build_rag_chain.generate_recommended_reply()` | 핵심 응답 생성 |
| 단일 발화 감정 | `src.emotion.analyze_emotion()` | Gemini caller 필요 |
| 대화 감정 흐름 | `src.emotion.analyze_dialogue_emotion()` | Gemini caller 필요 |
| 위험도 분석 | `src.emotion.analyze_risk()` | Gemini caller 필요 |
| 감정+위험도 통합 | `src.emotion.full_analysis()` | Streamlit 카드용 추천 |
| Gemini caller 생성 | `src.emotion.create_gemini_caller()` | Gemini key 필요 |
| Function Calling | `src.emotion.create_gemini_function_router()` | 자유 분석 요청용 |
| 검색 문서 표시 | `rag_result["retrieved_docs"]` | 디버그/근거 표시용 |
| 추천 예시 표시 | `rag_result["response_examples"]` | UI 확장용 |

---

## 11. 최소 구현 순서

1. `app/streamlit_app.py` 상단에 프로젝트 루트 path 설정
2. `run_rag_recommendation()` 추가
3. `build_utterances_from_messages()` 추가
4. `run_emotion_risk_analysis()` 추가
5. `st.session_state.latest_rag_result` 저장
6. `st.session_state.latest_analysis` 저장
7. 고정 분석 카드 제거
8. 고정 추천 답변 제거
9. fallback UI 추가
10. 실제 API key 기반 smoke test

---

## 12. 주의 사항

### API key

- secret 값 출력 금지
- `.streamlit/secrets.toml` 우선 사용
- `.env`는 fallback 용도

### 비용

`generate_recommended_reply()`와 `full_analysis()`를 동시에 호출하면 LLM 호출이 여러 번 발생한다.
초기 구현에서는 버튼 클릭 또는 사용자 입력 시에만 실행한다.

### 속도

RAG vector DB 로딩이 무거울 수 있다.
Streamlit에서는 캐시 사용 권장.

예:

```python
@st.cache_resource
def get_gemini_caller():
    from src.emotion import create_gemini_caller
    return create_gemini_caller()
```

RAG 전체 함수 `generate_recommended_reply()` 내부는 매번 데이터/벡터DB를 로딩한다.
성능 개선 단계에서는 `load_dataframes()`, `build_bm25()`, `load_vector_db()`, `load_example_vector_db()`, `load_llm()`을 캐시하는 wrapper를 별도로 둔다.

### 현재 앱 상태

현재 `app/streamlit_app.py`는 디자인과 레이아웃이 먼저 잡힌 상태다.
다음 작업은 UI 개편보다 프로젝트 함수 연결이 우선이다.
