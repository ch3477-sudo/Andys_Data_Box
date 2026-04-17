# Gemini Function Calling 변경 리포트

## 대상

- `src/emotion/llm_connector.py`
- `tests/test_emotion_llm_connector.py`

## 목적

- 기존 `llm_caller` 주입 구조 유지
- Gemini 중심 연결 모듈 추가
- Function Calling router 구조 추가
- 실제 API 호출 없이 검증 가능한 테스트 추가

---

## 1. `src/emotion/llm_connector.py`

### 역할

- Gemini API 연결 담당
- API key 로딩 담당
- 기존 emotion/risk 분석 함수와 Gemini 연결
- Function Calling router 제공

### 주요 구성

| 구성 | 내용 |
|---|---|
| `load_secret()` | Gemini API key 로딩 |
| `create_gemini_caller()` | 기존 `llm_caller(prompt)` 형식의 Gemini caller 생성 |
| `GeminiFunctionCallingRouter` | Gemini tool/function calling router |
| `dispatch_tool()` | 내부 분석 함수 local dispatch |
| `analyze_with_gemini_tools()` | router 실행용 간단 진입점 |

### API key 로딩 순서

1. Streamlit runtime secrets
2. `.streamlit/secrets.toml`
3. 환경변수
4. `data/.env`
5. 루트 `.env`

### placeholder 처리

다음 값은 미설정으로 처리:

- 빈 문자열
- `<...>` 형식
- `your_...` 형식
- `TODO`
- `TBD`
- `REPLACE_ME`
- `CHANGEME`

### Gemini caller

`create_gemini_caller()`는 기존 분석 함수가 요구하는 형태를 유지:

```python
llm_caller(prompt: str) -> str
```

기존 함수와 호환:

- `analyze_emotion(..., llm_caller=...)`
- `analyze_dialogue_emotion(..., llm_caller=...)`
- `analyze_risk(..., llm_caller=...)`
- `full_analysis(..., llm_caller=...)`

### Function Calling router

`GeminiFunctionCallingRouter`가 노출하는 tool:

| tool name | 연결 함수 |
|---|---|
| `analyze_single_emotion` | `analyze_emotion()` |
| `analyze_dialogue_emotion` | `analyze_dialogue_emotion()` |
| `analyze_dialogue_risk` | `analyze_risk()` |
| `full_dialogue_analysis` | `full_analysis()` |

### local dispatch

`dispatch_tool()` 추가 이유:

- Gemini API 호출 없이 tool 실행 검증 가능
- 테스트에서 네트워크 의존 제거
- Function Calling 대상 함수와 실제 실행 경로 일치

### 예외 처리

사용 예외:

```python
GeminiConnectorError
```

발생 조건:

- `GEMINI_API_KEY` 없음
- `google-genai` 미설치
- Gemini 응답 실패
- 응답 text 없음

### 설계 기준

- 기존 분석 모듈 직접 수정 최소화
- 기존 public API 유지
- Gemini 연결부를 별도 모듈로 분리
- secret 값 출력 금지
- live API 테스트 대신 fake client 주입 가능 구조

---

## 2. `tests/test_emotion_llm_connector.py`

### 역할

- Gemini connector 동작 검증
- 기존 API 호환성 검증
- secret 로딩 검증
- router dispatch 검증
- 네트워크 없는 테스트 보장

### 테스트 방식

- `unittest` 사용
- fake LLM 응답 사용
- fake Gemini client 사용
- 임시 디렉터리로 secret 파일 생성
- 실제 Gemini API 호출 없음

### 주요 테스트

| 테스트 | 검증 내용 |
|---|---|
| `test_existing_public_api_still_accepts_injected_llm_caller` | 기존 `analyze_emotion()` 호환 |
| `test_full_analysis_still_accepts_injected_llm_caller` | 기존 `full_analysis()` 호환 |
| `test_load_secret_reads_streamlit_toml_without_printing_value` | `.streamlit/secrets.toml` 로딩 |
| `test_load_secret_skips_placeholders_and_falls_back_to_env` | placeholder 무시, env fallback |
| `test_create_gemini_caller_supports_fake_client_without_network` | fake client 기반 Gemini caller 검증 |
| `test_router_dispatches_full_analysis_tool_locally` | router local dispatch 검증 |
| `test_router_rejects_unknown_tool` | 알 수 없는 tool 차단 |

### fake LLM 구성

`fake_emotion_llm()`이 prompt 내용에 따라 JSON 응답 반환:

- 위험도 분석 prompt → risk JSON
- 대화 감정 분석 prompt → dialogue emotion JSON
- 단일 감정 분석 prompt → single emotion JSON

### fake client 구성

`FakeClient` / `FakeModels` 사용:

- `generate_content()` 호출 기록
- 고정 JSON text 반환
- 실제 네트워크 호출 없음

### 검증 범위

포함:

- 기존 API 유지 여부
- secret loader 기본 동작
- Gemini caller factory 구조
- router dispatch 구조
- 예외 경로 일부

제외:

- 실제 Gemini API 응답 품질
- 실제 Function Calling round-trip
- Streamlit UI 연동
- RAG 파이프라인 연동

---

## 부수 변경

### `src/emotion/__init__.py`

추가 export:

- `DEFAULT_GEMINI_MODEL`
- `GeminiConnectorError`
- `GeminiFunctionCallingRouter`
- `ToolDispatchResult`
- `analyze_with_gemini_tools`
- `create_gemini_caller`
- `create_gemini_function_router`
- `load_secret`

목적:

- `from src.emotion import ...` 형태 지원
- connector 기능 외부 공개

### `requirements.txt`

추가 dependency:

```text
google-genai
```

목적:

- Gemini live 호출
- Gemini Function Calling 지원

---

## 실행 예시

### 기존 pipeline 방식

```python
from src.emotion import create_gemini_caller, full_analysis

caller = create_gemini_caller()

result = full_analysis(
    [
        "너 왜 또 늦었어?",
        "미안해, 일이 늦게 끝났어.",
    ],
    dialogue_id="sample_001",
    llm_caller=caller,
)
```

### router 방식

```python
from src.emotion import create_gemini_function_router

router = create_gemini_function_router()
response = router.route("대화의 감정과 갈등 위험도를 분석")
```

### local dispatch 방식

```python
from src.emotion import GeminiFunctionCallingRouter

router = GeminiFunctionCallingRouter(llm_caller=fake_llm)

result = router.dispatch_tool(
    "full_dialogue_analysis",
    utterances=["너 왜 또 늦었어?", "미안해."],
    dialogue_id="local_sample",
)
```

---

## 검증 결과

실행 명령:

```bash
python -m py_compile src/emotion/emotion_analyzer.py src/emotion/risk_analyzer.py src/emotion/llm_connector.py src/emotion/__init__.py
```

결과:

```text
성공
```

실행 명령:

```bash
python -m unittest discover -s tests
```

결과:

```text
Ran 7 tests
OK
```

---

## 남은 확인 항목

- 실제 `GEMINI_API_KEY` 기반 live 호출
- Gemini Function Calling 실제 round-trip
- Streamlit 화면 연결 여부
- RAG 응답 생성 단계와 연결 여부
- 운영용 에러 메시지 정리
