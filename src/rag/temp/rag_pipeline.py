import os
from pathlib import Path
from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from prompt_templates import rag_prompt


# --------------------------------------------------
# 0. 프로젝트 경로 설정
# 현재 파일: src/rag/rag_pipeline.py
# --------------------------------------------------
CURRENT_FILE = Path(__file__).resolve()
RAG_DIR = CURRENT_FILE.parent          # src/rag
SRC_DIR = RAG_DIR.parent               # src
DATA_DIR = SRC_DIR / "data"            # src/data
PROCESSED_DIR = DATA_DIR / "processed"
VECTORSTORE_DIR = PROCESSED_DIR / "vectorstore"

RAG_VECTORSTORE_PATH = VECTORSTORE_DIR / "rag"
EXAMPLE_VECTORSTORE_PATH = VECTORSTORE_DIR / "example"

ENV_PATH = SRC_DIR / ".env"   # .env가 src에 있을 때
# ENV_PATH = DATA_DIR / ".env"  # .env가 src/data에 있으면 이걸 사용


# --------------------------------------------------
# 1. 환경 변수 로드
# --------------------------------------------------
def load_environment() -> str:
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
    else:
        load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            f"OPENAI_API_KEY를 찾을 수 없습니다.\n"
            f".env 파일 위치를 확인하세요: {ENV_PATH}"
        )
    return api_key


OPENAI_API_KEY = load_environment()


# --------------------------------------------------
# 2. 경로/파일 확인 함수
# --------------------------------------------------
def check_path_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"경로를 찾을 수 없습니다: {path}\n"
            f"현재 SRC_DIR: {SRC_DIR}\n"
            f"현재 DATA_DIR 존재 여부: {DATA_DIR.exists()}\n"
            f"현재 VECTORSTORE_DIR 존재 여부: {VECTORSTORE_DIR.exists()}\n"
            f"VECTORSTORE_DIR 내용: "
            f"{[p.name for p in VECTORSTORE_DIR.iterdir()] if VECTORSTORE_DIR.exists() else '없음'}"
        )


def check_vectorstore_files(path: Path) -> None:
    required_files = ["index.faiss", "index.pkl"]
    missing_files = [f for f in required_files if not (path / f).exists()]

    if missing_files:
        raise FileNotFoundError(
            f"벡터스토어 폴더는 존재하지만 필요한 파일이 없습니다: {path}\n"
            f"누락 파일: {missing_files}\n"
            f"현재 폴더 내용: {[p.name for p in path.iterdir()] if path.exists() else '폴더 없음'}"
        )


# --------------------------------------------------
# 3. 임베딩 모델
# --------------------------------------------------
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=OPENAI_API_KEY
    )


# --------------------------------------------------
# 4. 벡터스토어 로드
# --------------------------------------------------
def load_vectorstores():
    print("CURRENT_FILE:", CURRENT_FILE)
    print("SRC_DIR:", SRC_DIR)
    print("DATA_DIR:", DATA_DIR)
    print("RAG_VECTORSTORE_PATH:", RAG_VECTORSTORE_PATH)
    print("EXAMPLE_VECTORSTORE_PATH:", EXAMPLE_VECTORSTORE_PATH)

    check_path_exists(RAG_VECTORSTORE_PATH)
    check_path_exists(EXAMPLE_VECTORSTORE_PATH)

    check_vectorstore_files(RAG_VECTORSTORE_PATH)
    check_vectorstore_files(EXAMPLE_VECTORSTORE_PATH)

    embeddings = get_embeddings()

    rag_vectorstore = FAISS.load_local(
        str(RAG_VECTORSTORE_PATH),
        embeddings,
        allow_dangerous_deserialization=True
    )

    example_vectorstore = FAISS.load_local(
        str(EXAMPLE_VECTORSTORE_PATH),
        embeddings,
        allow_dangerous_deserialization=True
    )

    return rag_vectorstore, example_vectorstore


# --------------------------------------------------
# 5. 검색 결과 포맷 함수
# --------------------------------------------------
def format_docs(docs) -> str:
    if not docs:
        return "관련 문서를 찾지 못했습니다."

    return "\n\n".join(
        f"[문서 {i+1}]\n{doc.page_content}"
        for i, doc in enumerate(docs)
    )


# --------------------------------------------------
# 6. RAG 파이프라인 클래스
# --------------------------------------------------
class RAGPipeline:
    def __init__(self):
        self.rag_vectorstore, self.example_vectorstore = load_vectorstores()

        self.rag_retriever = self.rag_vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )

        self.example_retriever = self.example_vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )

        self.llm = init_chat_model(
            "openai:gpt-4.1-mini",
            temperature=0.7
        )

        self.output_parser = StrOutputParser()
        self.generation_chain = rag_prompt | self.llm | self.output_parser

        self.context_chain = RunnableLambda(self.retrieve_context)
        self.example_chain = RunnableLambda(self.retrieve_examples)

        self.rag_chain = (
            self.context_chain
            | self.example_chain
            | self.generation_chain
        )

    # 1단계: 문맥 검색
    def retrieve_context(self, user_input: str) -> dict:
        retrieved_docs = self.rag_retriever.invoke(user_input)
        retrieved_context = format_docs(retrieved_docs)

        return {
            "user_input": user_input,
            "retrieved_context": retrieved_context
        }

    # 2단계: 유사 응답 예시 검색
    def retrieve_examples(self, inputs: dict) -> dict:
        user_input = inputs["user_input"]

        retrieved_example_docs = self.example_retriever.invoke(user_input)
        retrieved_examples = format_docs(retrieved_example_docs)

        return {
            "user_input": user_input,
            "retrieved_context": inputs["retrieved_context"],
            "retrieved_examples": retrieved_examples
        }

    # 최종 답변 생성
    def generate_response(self, user_input: str) -> str:
        return self.rag_chain.invoke(user_input)

    # 디버그용
    def generate_response_with_debug(self, user_input: str) -> dict:
        step1 = self.retrieve_context(user_input)
        step2 = self.retrieve_examples(step1)
        result = self.generation_chain.invoke(step2)

        return {
            "user_input": user_input,
            "retrieved_context": step1["retrieved_context"],
            "retrieved_examples": step2["retrieved_examples"],
            "result": result
        }


# --------------------------------------------------
# 7. 실행
# --------------------------------------------------
def main():
    print("현재 작업 경로:", os.getcwd())
    print("ROOT_DIR:", RAG_DIR)
    print("DATA_DIR 존재 여부:", DATA_DIR.exists())
    print("VECTORSTORE_DIR 존재 여부:", VECTORSTORE_DIR.exists())

    pipeline = RAGPipeline()

    test_input = "요즘 너무 지치고 내가 잘하고 있는지도 모르겠어."
    result = pipeline.generate_response_with_debug(test_input)

    print("\n===== 사용자 입력 =====")
    print(result["user_input"])

    print("\n===== 검색된 관련 문서 =====")
    print(result["retrieved_context"])

    print("\n===== 검색된 유사 응답 예시 =====")
    print(result["retrieved_examples"])

    print("\n===== 최종 추천 결과 =====")
    print(result["result"])


if __name__ == "__main__":
    main()