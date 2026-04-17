# ============================================================
# - rag_documents_with_text.csv를 불러옴
# - response_pairs_with_text.csv를 불러옴
# - rag_text를 임베딩하여 검색용 FAISS 벡터DB 생성
# - response_example_text를 임베딩하여 응답예시용 FAISS 벡터DB 생성
# - metadata를 함께 저장함
# ============================================================

from pathlib import Path
import os
import time
import pandas as pd
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


# ============================================================
# 1. 경로 설정
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

RAG_TEXT_PATH = PROCESSED_DATA_DIR / "rag_documents_with_text.csv"
RESPONSE_TEXT_PATH = PROCESSED_DATA_DIR / "response_pairs_with_text.csv"

VECTOR_DB_DIR = PROCESSED_DATA_DIR / "faiss_rag_db"
EXAMPLE_VECTOR_DB_DIR = PROCESSED_DATA_DIR / "faiss_example_db"

MAX_TEXT_LENGTH = 4000


# ============================================================
# 2. API KEY 로드
#    우선순위: .streamlit/secrets.toml -> .env
# ============================================================
def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip('"').strip("'")
    if not normalized:
        return True
    return (
        normalized.startswith("<")
        or normalized.startswith("your_")
        or normalized.upper() in {"TODO", "TBD", "REPLACE_ME", "CHANGEME"}
    )


def _load_from_secrets_toml(key: str) -> str | None:
    secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return None

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        with secrets_path.open("rb") as f:
            secret_data = tomllib.load(f)
    except Exception:
        return None

    secret_value = secret_data.get(key)
    if secret_value and not _is_placeholder(str(secret_value)):
        return str(secret_value)
    return None


def _load_from_env_files(key: str) -> str | None:
    for env_path in (PROJECT_ROOT / "data" / ".env", PROJECT_ROOT / ".env"):
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)

    env_value = os.getenv(key)
    if env_value and not _is_placeholder(env_value):
        return env_value
    return None


def load_api_key(key: str = "OPENAI_API_KEY") -> str:
    openai_api_key = _load_from_secrets_toml(key) or _load_from_env_files(key)
    if not openai_api_key:
        raise ValueError(
            f"{key}가 설정되지 않음. .streamlit/secrets.toml 또는 .env를 확인하세요."
        )
    return openai_api_key


OPENAI_API_KEY = load_api_key("OPENAI_API_KEY")


# ============================================================
# 3. 문자열 처리 함수
# ============================================================
def clean_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def truncate_text(text, max_len=4000):
    text = clean_text(text)
    if len(text) <= max_len:
        return text
    return text[:max_len]


# ============================================================
# 4. CSV 로드
# ============================================================
if not RAG_TEXT_PATH.exists():
    raise FileNotFoundError(f"파일을 찾을 수 없음: {RAG_TEXT_PATH}")

if not RESPONSE_TEXT_PATH.exists():
    raise FileNotFoundError(f"파일을 찾을 수 없음: {RESPONSE_TEXT_PATH}")

rag_df = pd.read_csv(RAG_TEXT_PATH)
response_df = pd.read_csv(RESPONSE_TEXT_PATH)

print("===== RAG CSV 로드 완료 =====")
print(rag_df.shape)
print(rag_df.columns.tolist())

print("\n===== RESPONSE CSV 로드 완료 =====")
print(response_df.shape)
print(response_df.columns.tolist())


# ============================================================
# 5. rag_text 유효성 확인
# ============================================================
if "rag_text" not in rag_df.columns:
    raise ValueError("rag_text 컬럼이 없음.")

rag_df["rag_text"] = rag_df["rag_text"].astype(str).str.strip()
rag_df = rag_df[rag_df["rag_text"] != ""].copy()

print("\n===== 유효 RAG 문서 수 =====")
print(len(rag_df))


# ============================================================
# 6. response_example_text 유효성 확인
# ============================================================
if "response_example_text" not in response_df.columns:
    raise ValueError("response_example_text 컬럼이 없음.")

response_df["response_example_text"] = response_df["response_example_text"].astype(str).str.strip()
response_df = response_df[response_df["response_example_text"] != ""].copy()

print("\n===== 유효 RESPONSE 예시 수 =====")
print(len(response_df))


# ============================================================
# 7. rag texts / metadatas 준비
# ============================================================
def build_rag_texts_and_metadatas(rag_df: pd.DataFrame):
    texts = []
    metadatas = []

    for _, row in rag_df.iterrows():
        text = truncate_text(row["rag_text"], MAX_TEXT_LENGTH)
        texts.append(text)

        metadatas.append({
            "dialogue_id": clean_text(row.get("dialogue_id", "")),
            "file_name": clean_text(row.get("file_name", "")),
            "relation": clean_text(row.get("relation", "")),
            "situation": clean_text(row.get("situation", "")),
            "speaker_emotion": clean_text(row.get("speaker_emotion", "")),
            "listener_behavior": clean_text(row.get("listener_behavior", "")),
            "listener_empathy_tags": clean_text(row.get("listener_empathy_tags", "")),
            "risk_level": clean_text(row.get("risk_level", "")),
            "conflict_keywords": clean_text(row.get("conflict_keywords", "")),
            "turn_count": clean_text(row.get("turn_count", "")),
            "terminated": clean_text(row.get("terminated", "")),
        })

    return texts, metadatas


# ============================================================
# 8. response example texts / metadatas 준비
# ============================================================
def build_example_texts_and_metadatas(response_df: pd.DataFrame):
    example_texts = []
    example_metadatas = []

    for _, row in response_df.iterrows():
        text = truncate_text(row["response_example_text"], MAX_TEXT_LENGTH)
        example_texts.append(text)

        example_metadatas.append({
            "dialogue_id": clean_text(row.get("dialogue_id", "")),
            "relation": clean_text(row.get("relation", "")),
            "situation": clean_text(row.get("situation", "")),
            "speaker_emotion": clean_text(row.get("speaker_emotion", "")),
            "listener_empathy": clean_text(row.get("listener_empathy", "")),
            "terminate": clean_text(row.get("terminate", "")),
            "listener_response": clean_text(row.get("listener_response", "")),
        })

    return example_texts, example_metadatas


texts, metadatas = build_rag_texts_and_metadatas(rag_df)
example_texts, example_metadatas = build_example_texts_and_metadatas(response_df)

print("\n===== 첫 번째 RAG metadata 샘플 =====")
print(metadatas[0])

print("\n===== 첫 번째 RESPONSE metadata 샘플 =====")
print(example_metadatas[0])


# ============================================================
# 9. 임베딩 모델 준비
# ============================================================
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY,
)


# ============================================================
# 10. RAG FAISS 벡터DB 생성
# ============================================================
print("\n===== RAG FAISS 벡터DB 생성 시작 =====")
start_time = time.time()

vector_db = FAISS.from_texts(
    texts=texts,
    embedding=embeddings,
    metadatas=metadatas,
)

elapsed = time.time() - start_time

print("===== RAG FAISS 벡터DB 생성 완료 =====")
print(f"소요 시간: {round(elapsed, 2)}초")


# ============================================================
# 11. RESPONSE EXAMPLE FAISS 벡터DB 생성
# ============================================================
print("\n===== RESPONSE EXAMPLE FAISS 벡터DB 생성 시작 =====")
example_start_time = time.time()

example_vector_db = FAISS.from_texts(
    texts=example_texts,
    embedding=embeddings,
    metadatas=example_metadatas,
)

example_elapsed = time.time() - example_start_time

print("===== RESPONSE EXAMPLE FAISS 벡터DB 생성 완료 =====")
print(f"소요 시간: {round(example_elapsed, 2)}초")


# ============================================================
# 12. 저장
# ============================================================
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
vector_db.save_local(str(VECTOR_DB_DIR))

EXAMPLE_VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
example_vector_db.save_local(str(EXAMPLE_VECTOR_DB_DIR))

print("\n===== 저장 완료 =====")
print(VECTOR_DB_DIR)
print(EXAMPLE_VECTOR_DB_DIR)