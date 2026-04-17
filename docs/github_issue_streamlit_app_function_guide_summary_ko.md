# Streamlit 앱 연동 문서 작성 요약

## 개요

`app/streamlit_app.py`는 현재 UI 목업 중심으로 구성되어 있다.

화면 레이아웃, 채팅 UI, 분석 카드, 추천 답변, 대화 히스토리 영역은 존재하지만 실제 프로젝트 기능과는 아직 연결되지 않은 상태다.

이에 따라 Streamlit 앱에서 어떤 프로젝트 함수와 기능을 사용해야 하는지 정리한 문서를 추가했다.

자세한 내용은 아래 문서 참고.

```text
docs/streamlit_app_project_function_guide.md
```

---

## 현재 앱 상태

대상 파일:

```text
app/streamlit_app.py
```

현재 주요 함수:

```text
apply_custom_css()
render_analysis_card()
render_history_item()
main()
```

현재 한계:

- 감정 분석 카드 고정값 사용
- 위험도 분석 카드 고정값 사용
- 추천 답변 고정값 사용
- 대화 히스토리 고정값 사용
- RAG 추천 답변 로직 미연결
- 감정/위험도 분석 로직 미연결
- Gemini Function Calling router 미연결

---

## 작성한 문서

추가 문서:

```text
docs/streamlit_app_project_function_guide.md
```

문서 목적:

- 현재 Streamlit UI와 연결해야 할 프로젝트 함수 정리
- 함수별 import 경로 제공
- 실제 사용 예시 제공
- Streamlit session state 연결 방식 제안
- 고정값 UI를 동적 분석 결과로 바꾸는 흐름 정리

---

## 문서에 정리한 주요 기능

### API key 로딩

```python
from src.rag.api_key_loader import load_api_key
```

사용 목적:

- `OPENAI_API_KEY` 로딩
- `.streamlit/secrets.toml` 우선 사용
- `data/.env`, 루트 `.env` fallback

### RAG 추천 답변 생성

```python
from src.rag.build_rag_chain import generate_recommended_reply
```

사용 목적:

- 사용자 입력 기반 추천 답변 생성
- 관련 RAG 문서 검색
- 상황 요약 생성
- 응답 예시 반환
- 최종 추천 답변 반환

### 감정 분석

```python
from src.emotion import create_gemini_caller
from src.emotion import analyze_emotion
from src.emotion import analyze_dialogue_emotion
```

사용 목적:

- 단일 발화 감정 분석
- 대화 전체 감정 흐름 분석
- 감정 라벨, 신뢰도, 대응 전략, 감정 시퀀스 반환

### 위험도 분석

```python
from src.emotion import analyze_risk
from src.emotion import full_analysis
```

사용 목적:

- 갈등 위험도 분석
- 감정 분석 + 위험도 분석 통합 실행
- 위험도 점수, 위험 등급, 추천 대응 반환

### Gemini Function Calling

```python
from src.emotion import create_gemini_function_router
```

사용 목적:

- Gemini가 내부 분석 tool을 선택하도록 구성
- 감정 분석, 위험도 분석, 통합 분석 도구 연결

---

## 문서에 제안한 Streamlit helper 함수

```python
build_utterances_from_messages()
run_rag_recommendation()
run_emotion_risk_analysis()
build_analysis_cards()
build_recommendations()
```

역할:

- UI 코드와 분석 로직 분리
- session state 기반 데이터 흐름 정리
- 분석 카드와 추천 답변을 동적으로 표시하기 위한 중간 변환 처리

---

## 권장 연동 흐름

1. 사용자가 메시지 입력
2. `st.session_state.messages`에 사용자 메시지 저장
3. `generate_recommended_reply()` 실행
4. 현재 메시지 목록에서 발화 리스트 생성
5. `full_analysis()` 실행
6. 결과를 session state에 저장
   - `latest_rag_result`
   - `latest_analysis`
7. 추천 답변을 assistant 메시지로 추가
8. 감정/위험도 카드를 실제 분석 결과로 렌더링
9. 추천 답변 목록을 실제 RAG 결과로 렌더링

---

## 검증

문서 내 필수 함수명 포함 여부 확인 완료.

확인 결과:

```text
docs_function_guide_ok
```

포함 확인된 주요 항목:

- `generate_recommended_reply`
- `load_api_key`
- `create_gemini_caller`
- `full_analysis`
- `create_gemini_function_router`
- `build_utterances_from_messages`
- `run_rag_recommendation`
- `run_emotion_risk_analysis`

secret 값은 문서에 포함하지 않음.

---

## 기대 효과

- Streamlit UI와 backend 함수 연결 기준 명확화
- 구현 전 혼선 감소
- 중복 연동 코드 방지
- 실제 import 경로와 사용 예시 제공
- 정적 UI를 실제 동작 UI로 전환하기 위한 순서 제공
- 후속 Streamlit 리팩터링 기준 문서 확보

---

## 남은 작업

- `docs/streamlit_app_project_function_guide.md` 기준으로 `app/streamlit_app.py` 실제 연동
- 고정 감정/위험도 카드 제거
- 고정 추천 답변 제거
- `generate_recommended_reply()` 결과 연결
- `full_analysis()` 결과 연결
- Streamlit cache 적용 검토
- 실제 API key 기반 smoke test 진행
