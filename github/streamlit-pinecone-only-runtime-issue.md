# [Issue] Streamlit Community Cloud 배포를 위한 `test_app.py` Pinecone-only 런타임 전환

## 배경

`app/test_app.py`를 Streamlit Community Cloud에 배포하려면 GitHub 저장소에 포함된 파일과 Streamlit Secrets만으로 앱이 실행되어야 한다.

기존 RAG 런타임은 Pinecone vector DB를 사용하면서도 `generate_recommended_reply()` 시작 단계에서 로컬 CSV 파일을 먼저 읽었다.

문제가 되는 파일:

- `data/processed/rag_documents_with_text.csv`
- `data/processed/response_pairs_with_text.csv`

하지만 `data/`와 `*.csv`는 Git 추적 대상이 아니며, 배포 런타임에서 CSV 전처리나 vector DB 생성 단계를 실행하지 않는 것이 확정된 방향이다.

## 문제

현재 배포 목표는 다음과 같다.

- Streamlit Community Cloud에서 `app/test_app.py`만 앱 entrypoint로 사용
- API key는 Streamlit Cloud Secrets에 등록
- 이미 생성된 Pinecone index를 런타임에서 사용
- 배포 런타임에서는 로컬 CSV 파일에 의존하지 않음
- CSV 전처리 및 Pinecone vector DB 생성 스크립트는 build/setup-time 도구로만 유지

기존 코드에서는 `src/rag/build_rag_chain.py`의 `generate_recommended_reply()`가 기본 실행 경로에서 `load_dataframes()`와 `build_bm25()`를 호출했기 때문에, Pinecone index가 준비되어 있어도 CSV 파일이 없으면 앱 실행이 실패할 수 있었다.

## 결정 사항

Ralplan 결과에 따라 다음 방향으로 진행했다.

1. `app/test_app.py` 기본 런타임은 Pinecone-only로 전환한다.
2. `method="rrf"`는 앱 기본 호출 호환성을 위해 유지하되, 로컬 CSV/BM25 입력이 없으면 Pinecone dense retrieval로 동작한다.
3. `bm25` 검색은 로컬 CSV와 BM25 index가 명시적으로 준비된 경우에만 사용한다.
4. `rank_bm25`는 모듈 import 시점이 아니라 `build_bm25()` 호출 시점에만 import한다.
5. 응답 예시 후보 생성은 `response_df=None` 또는 빈 DataFrame에서도 Pinecone example index만으로 동작하게 한다.
6. Streamlit Community Cloud dependency file 우선순위를 문서화한다.

## 변경 내용

### 1. Pinecone-only RAG 런타임

파일: `src/rag/build_rag_chain.py`

- `generate_recommended_reply()` 기본값에 `use_local_csv=False` 추가
- 기본 실행 경로에서 `load_dataframes()` / `build_bm25()` 호출 제거
- `method="rrf"`에서 CSV/BM25가 없으면 Pinecone dense retrieval로 fallback
- `method="bm25"`는 CSV/BM25가 없으면 명확한 `ValueError` 발생
- `rank_bm25` import를 `build_bm25()` 내부로 이동
- `response_df`가 없어도 example Pinecone 검색 결과로 추천 답변 후보 생성 가능하게 변경

### 2. 배포 런타임 테스트 추가

파일: `tests/test_rag_streamlit_deploy_runtime.py`

추가 검증:

- `generate_recommended_reply()` 기본 경로가 CSV를 읽지 않음
- fake Pinecone vector store와 fake LLM으로 Pinecone-only 동작 검증
- `build_response_example_candidates(response_df=None, ...)` 동작 검증
- `method="bm25"`가 로컬 CSV 없이 실행되면 명확히 실패하는지 검증
- `app_service.run_chat_analysis()`가 기존처럼 `method="rrf", k=3` 계약을 유지하는지 검증

### 3. 의존성 정리

파일: `requirements.txt`

- `streamlit` 추가

참고:

- 현재 저장소에는 `environment.yml`도 존재한다.
- Streamlit Community Cloud에서는 `environment.yml`이 root `requirements.txt`보다 우선될 수 있으므로, 현재 Cloud 배포 기준 활성 dependency file은 `environment.yml`로 문서화했다.
- `requirements.txt`는 pip 기반 로컬 실행 또는 추후 pip-only 배포를 위해 보강했다.

### 4. 배포 가이드 추가

파일: `docs/streamlit_community_cloud_deploy.md`

포함 내용:

- Streamlit app entrypoint: `app/test_app.py`
- 필수 Secrets:
  - `OPENAI_API_KEY`
  - `GEMINI_API_KEY`
  - `PINECONE_API_KEY`
- 필수 Pinecone indexes:
  - `andys-rag-documents`
  - `andys-rag-examples`
- CSV 파일은 build-time input이며 runtime deployment file이 아님
- `environment.yml`과 `requirements.txt`가 함께 있을 때의 dependency file 주의사항

## 검증 결과

Ralph 실행 중 fresh verification으로 확인한 결과:

```text
python -m unittest discover tests
Ran 29 tests in 6.075s
OK
```

추가 확인:

```text
app/test_app.py import smoke: IMPORT_SMOKE_OK
required secrets load through load_api_key: SECRETS_LOAD_OK
git diff --check on changed files: passed
```

Live Pinecone smoke는 로컬에서 별도 확인 완료된 것으로 정리했고, 추가 실행은 생략했다.

## 변경 파일

- `src/rag/build_rag_chain.py`
- `tests/test_rag_streamlit_deploy_runtime.py`
- `requirements.txt`
- `docs/streamlit_community_cloud_deploy.md`
- `.omx/plans/prd-test-app-streamlit-deploy-pinecone-only-20260422T022311Z.md`
- `.omx/plans/test-spec-test-app-streamlit-deploy-pinecone-only-20260422T022311Z.md`

## 완료 기준

- [x] `app/test_app.py` 기본 경로에서 로컬 CSV 파일을 요구하지 않음
- [x] Pinecone RAG document index와 example index를 런타임 검색 소스로 사용
- [x] 기존 `app_service.run_chat_analysis()`의 `method="rrf", k=3` 호출 계약 유지
- [x] `bm25`는 로컬 CSV 기반 평가/실험용 경로로 분리
- [x] `rank_bm25` import 문제를 앱 import 시점에서 제거
- [x] 배포 문서에 entrypoint, secrets, index, dependency file, CSV runtime 제외 조건 명시
- [x] 전체 unit test 통과

## 남은 주의사항

- 실제 Streamlit Community Cloud 배포 시 Secrets 화면에 세 API key를 직접 등록해야 한다.
- `.streamlit/secrets.toml`의 실제 key 값은 Git에 올리면 안 된다.
- Pinecone index 이름을 바꾸면 `src/rag/pinecone_vector_store.py`의 index 상수와 배포 문서를 함께 갱신해야 한다.
- `environment.yml`이 존재하는 동안 Streamlit Cloud는 `requirements.txt`가 아니라 `environment.yml`을 우선 사용할 수 있다.
