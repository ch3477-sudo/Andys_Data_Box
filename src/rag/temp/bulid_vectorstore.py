import os
from pathlib import Path
import pandas as pd

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


CURRENT_FILE = Path(__file__).resolve()
RAG_DIR = CURRENT_FILE.parent
SRC_DIR = RAG_DIR.parent
DATA_DIR = SRC_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
VECTORSTORE_DIR = PROCESSED_DIR / "vectorstore"

RAG_DATA_PATH = DATA_DIR / "rag_documents.csv"
PAIR_DATA_PATH = DATA_DIR / "response_pairs.csv"

RAG_SAVE_PATH = VECTORSTORE_DIR / "rag"
EXAMPLE_SAVE_PATH = VECTORSTORE_DIR / "example"

ENV_PATH = SRC_DIR / ".env"
# ENV_PATH = DATA_DIR / ".env"


def load_environment() -> str:
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(f"OPENAI_API_KEY를 찾을 수 없습니다. .env 위치: {ENV_PATH}")
    return api_key


OPENAI_API_KEY = load_environment()


def check_file_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")


def load_data():
    check_file_exists(RAG_DATA_PATH)
    check_file_exists(PAIR_DATA_PATH)

    rag_df = pd.read_csv(RAG_DATA_PATH)
    pair_df = pd.read_csv(PAIR_DATA_PATH)

    print("rag_documents.csv shape:", rag_df.shape)
    print("response_pairs.csv shape:", pair_df.shape)
    print("rag_df columns:", rag_df.columns.tolist())
    print("pair_df columns:", pair_df.columns.tolist())

    return rag_df, pair_df


def build_rag_documents(rag_df: pd.DataFrame):
    docs = []
    for _, row in rag_df.iterrows():
        text = f"""
관계: {row['relation']}
상황: {row['situation']}
화자 감정: {row['speaker_emotion']}
청자 행동: {row['listener_behavior']}

전체 대화:
{row['full_dialogue']}
""".strip()

        docs.append(
            Document(
                page_content=text,
                metadata={"dialogue_id": row.get("dialogue_id", ""), "source": "rag_documents"}
            )
        )
    return docs


def build_example_documents(pair_df: pd.DataFrame):
    docs = []
    for _, row in pair_df.iterrows():
        text = f"""
관계: {row['relation']}
상황: {row['situation']}
화자 감정: {row['speaker_emotion']}

응답 직전 문맥:
{row['context_before_response']}

청자 응답:
{row['listener_response']}
""".strip()

        docs.append(
            Document(
                page_content=text,
                metadata={"dialogue_id": row.get("dialogue_id", ""), "source": "response_pairs"}
            )
        )
    return docs


def split_documents(docs, chunk_size=500, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(docs)


def get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=OPENAI_API_KEY
    )


def build_and_save_vectorstore(docs, save_path: Path, embeddings):
    if not docs:
        raise ValueError(f"저장할 문서가 없습니다: {save_path}")

    save_path.mkdir(parents=True, exist_ok=True)

    print(f"\n[저장 시작] {save_path}")
    print("문서 개수:", len(docs))
    print("첫 문서 일부:", docs[0].page_content[:200])

    try:
        vectorstore = FAISS.from_documents(docs, embeddings)
        vectorstore.save_local(str(save_path))
        print(f"[저장 완료] {save_path}")
        print("저장된 파일:", [p.name for p in save_path.iterdir()])
    except Exception as e:
        print(f"[실패] {save_path}")
        print("에러 타입:", type(e).__name__)
        print("에러 메시지:", str(e))
        raise


def main():
    print("CURRENT_FILE:", CURRENT_FILE)
    print("SRC_DIR:", SRC_DIR)
    print("DATA_DIR:", DATA_DIR)
    print("VECTORSTORE_DIR:", VECTORSTORE_DIR)
    print("ENV_PATH:", ENV_PATH)
    print("API KEY 존재:", bool(OPENAI_API_KEY))
    print("API KEY 앞 12글자:", OPENAI_API_KEY[:12])

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    rag_df, pair_df = load_data()

    rag_docs = build_rag_documents(rag_df)
    example_docs = build_example_documents(pair_df)

    print("원본 RAG 문서 수:", len(rag_docs))
    print("원본 Example 문서 수:", len(example_docs))

    split_rag_docs = split_documents(rag_docs)
    split_example_docs = split_documents(example_docs)

    print("분할된 RAG chunk 수:", len(split_rag_docs))
    print("분할된 Example chunk 수:", len(split_example_docs))

    embeddings = get_embeddings()

    print("\n[임베딩 단독 테스트]")
    test_vec = embeddings.embed_query("테스트 문장입니다.")
    print("임베딩 길이:", len(test_vec))

    build_and_save_vectorstore(split_rag_docs, RAG_SAVE_PATH, embeddings)
    build_and_save_vectorstore(split_example_docs, EXAMPLE_SAVE_PATH, embeddings)

    print("\n모든 vectorstore 생성 완료")
    print("VECTORSTORE_DIR 내용:", [p.name for p in VECTORSTORE_DIR.iterdir()])


if __name__ == "__main__":
    main()