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
BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

RAG_TEXT_PATH = PROCESSED_DATA_DIR / "rag_documents_with_text.csv"
RESPONSE_TEXT_PATH = PROCESSED_DATA_DIR / "response_pairs_with_text.csv"

VECTOR_DB_DIR = PROCESSED_DATA_DIR / "faiss_rag_db"
EXAMPLE_VECTOR_DB_DIR = PROCESSED_DATA_DIR / "faiss_example_db"

MAX_TEXT_LENGTH = 4000


# ============================================================
# 2. 환경변수 로드
# ============================================================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않음.")


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