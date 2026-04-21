# GitHub Issue 초안: test_app AI 추천 답변 자연스러움 개선

## 권장 이슈 제목

```text
Show LLM-generated labeled recommendations in test_app and keep RAG examples as evidence
```

## 요약

`app/test_app.py`의 `AI 추천 답변` 영역이 부자연스럽게 보이는 문제가 있었습니다. 원인은 전처리 파일이나 벡터 DB 부족이라기보다, 사용자에게 보여주는 추천 답변이 LLM이 자연스럽게 재작성한 최종 문장이 아니라 RAG에서 가져온 예시성 문장에 가까운 `recommended_replies` 기반 텍스트였기 때문입니다.

이번 변경은 `AI 추천 답변`에는 LLM이 생성한 자연스러운 세 유형 답변을 보여주고, RAG에서 검색된 예시는 별도 근거 섹션으로 유지하도록 출력 파이프라인을 분리합니다.

---

## 문제 상황

기존 흐름에서는 다음 구조가 섞여 있었습니다.

- `recommended_replies`: RAG response example에서 선택된 예시 답변
- `reply_candidates`: 화면의 `AI 추천 답변`에 출력되는 답변 목록
- `result_text`: LLM이 생성한 최종 분석/추천 결과

최근 응답 유형 라벨 작업 이후 `reply_candidates`가 `recommended_replies`에서 만들어지면서, `AI 추천 답변`에 raw RAG 예시성 문장이 표시될 수 있었습니다. 이 때문에 문장이 맥락상 어색하거나 실제 사용자에게 바로 보내기 부자연스러워 보일 수 있었습니다.

---

## 결정 사항

### 사용자에게 보여줄 답변

`AI 추천 답변` 영역에는 LLM이 새로 생성한 자연스러운 답변을 표시합니다.

형식:

```text
[공감형] ...
[완화형] ...
[비난 회피형] ...
```

### RAG 예시

RAG에서 가져온 예시는 삭제하지 않고, 별도 근거/참고 섹션으로 표시합니다.

### 하지 않는 것

이번 1차 작업에서는 아래를 하지 않습니다.

- 전처리 파일 수정
- 벡터 DB 재생성
- Pinecone 재빌드
- 모델 변경
- UI 디자인 대폭 변경

---

## 구현 내용

### `src/rag/build_rag_chain.py`

프롬프트 출력 형식을 변경했습니다.

기존:

```text
[추천 답변 1]
[추천 답변 2]
```

변경:

```text
[공감형]
...

[완화형]
...

[비난 회피형]
...
```

이제 LLM이 세 전략 라벨에 맞춰 직접 자연스러운 사용자-facing 답변을 생성하도록 유도합니다.

### `src/app_rag_result_parser.py`

`extract_reply_candidates()`가 LLM 출력에서 다음 섹션을 우선 파싱합니다.

```text
[공감형]
[완화형]
[비난 회피형]
```

해당 섹션이 있으면 `reply_candidates`는 LLM 생성 답변을 사용합니다.

### `src/app_payload_formatter.py`

기존 RAG 근거인 `recommended_replies`는 유지하되, `reply_candidates`는 LLM 생성 섹션을 우선 사용하도록 바꿨습니다.

우선순위:

1. LLM 생성 `[공감형]`, `[완화형]`, `[비난 회피형]`
2. 기존 `[추천 답변 1~3]`
3. fallback RAG 예시

### `app/test_app.py`

`AI 추천 답변` 영역은 기존처럼 `reply_candidates`를 표시합니다.  
추가로 `recommended_replies`가 있으면 `RAG 참고 예시` 섹션을 별도로 보여줍니다.

즉:

- 위쪽: 사용자에게 보낼 자연스러운 LLM 생성 답변
- 아래쪽: 검색된 RAG 예시 근거

---

## 검증 결과

### 신규/수정 테스트

```text
python -m unittest tests.test_app_recommendation_payload
Ran 2 tests
OK
```

검증 내용:

- LLM 출력의 `[공감형]`, `[완화형]`, `[비난 회피형]` 섹션 파싱
- `reply_candidates`가 LLM 생성 답변을 우선 사용
- `recommended_replies`가 RAG 근거로 별도 보존

### 관련 테스트

```text
python -m unittest tests.test_app_recommendation_payload tests.test_rag_response_type_mapping
Ran 7 tests
OK
```

### 전체 테스트

```text
python -m unittest discover -s tests
Ran 25 tests
OK
```

### 정적 검증

```text
py_compile 통과
git diff --check 통과
LSP diagnostics: 0 errors
```

---

## 변경 파일

```text
src/rag/build_rag_chain.py
src/app_rag_result_parser.py
src/app_payload_formatter.py
app/test_app.py
tests/test_app_recommendation_payload.py
tests/test_rag_response_type_mapping.py
```

관련 산출물:

```text
.omx/context/test-app-ai-recommendation-naturalness-20260421T093258Z.md
.omx/interviews/test-app-ai-recommendation-naturalness-20260421T093258Z.md
.omx/specs/deep-interview-test-app-ai-recommendation-naturalness.md
.omx/plans/prd-test-app-ai-recommendation-naturalness-20260421T094020Z.md
.omx/plans/test-spec-test-app-ai-recommendation-naturalness-20260421T094020Z.md
```

---

## 기대 효과

- `AI 추천 답변`이 더 자연스러운 사용자-facing 문장으로 표시됨
- 세 유형 라벨이 유지됨
- RAG 예시 근거도 사라지지 않음
- 전처리/벡터DB 재생성 없이 출력 품질을 먼저 개선함

---

## 남은 리스크

1. LLM이 출력 형식을 어기면 파서가 fallback 경로를 사용할 수 있습니다.
2. 실제 사용자 체감 품질은 샘플 입력으로 추가 확인이 필요합니다.
3. RAG 예시 자체의 품질이 낮은 경우, 이후 2차로 `response_style` 컬럼/벡터 DB 재생성을 검토할 수 있습니다.

---

## 후속 작업 후보

- 실제 갈등 상황 샘플 10~20개로 자연스러움 수동 평가
- `AI 추천 답변`과 `RAG 참고 예시`의 UI 배치 개선
- LLM 출력 형식 실패 시 자동 보정 로직 강화
