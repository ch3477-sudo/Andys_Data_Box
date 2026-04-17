# ============================================================
# - baseline 답변과 RAG 답변 비교
# - 비교 결과 CSV 저장
# - 정성 평가 컬럼 추가
# ============================================================

from pathlib import Path

import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

try:
    from .api_key_loader import load_api_key
    from .build_rag_chain import generate_recommended_reply
except ImportError:
    from api_key_loader import load_api_key
    from build_rag_chain import generate_recommended_reply


# ============================================================
# 1. 경로 설정
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = PROCESSED_DATA_DIR / "baseline_vs_rag_results.csv"


# ============================================================
# 3. LLM 준비
# ============================================================
def load_llm(openai_api_key: str) -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0,
        api_key=openai_api_key,
    )


BASELINE_PROMPT = PromptTemplate.from_template(
    """
너는 연인 갈등 상황에서 답변 문장을 추천하는 도우미다.

사용자 질문만 보고,
메신저에 바로 보낼 수 있는 자연스러운 한국어 답변 2개를 작성하라.
너무 길지 않게 작성하고,
공격적이거나 비난하는 말은 피하라.

사용자 질문:
{question}

아래 형식으로 출력하라.

[추천 답변 1]
...

[추천 답변 2]
...
"""
)


# ============================================================
# 4. 테스트 질문
# ============================================================
def get_test_questions() -> list[str]:
    return [
        "남자친구가 내 말을 제대로 안 들어주는 것 같아서 서운해. 어떻게 보내면 좋을까?",
        "내가 힘들다고 했는데 공감 없이 넘어가서 속상해.",
        "사소한 말다툼이 반복돼서 지쳐. 뭐라고 보내야 할까?",
    ]


# ============================================================
# 5. baseline / rag 생성
# ============================================================
def generate_baseline_reply(question: str, chat_model: ChatOpenAI) -> str:
    baseline_prompt = BASELINE_PROMPT.format(question=question)
    llm_response = chat_model.invoke(baseline_prompt)
    return llm_response.content


def compare_baseline_vs_rag() -> pd.DataFrame:
    openai_api_key = load_api_key()
    chat_model = load_llm(openai_api_key)

    comparison_rows = []
    test_questions = get_test_questions()

    for question in test_questions:
        print(f"\n===== 질문 =====\n{question}")

        baseline_answer = generate_baseline_reply(question, chat_model)
        rag_output = generate_recommended_reply(question, method="rrf", k=3)
        rag_answer = rag_output["result_text"]

        comparison_rows.append({
            "question": question,
            "baseline_answer": baseline_answer,
            "rag_answer": rag_answer,
            "empathy_better": "",
            "specificity_better": "",
            "safer_expression": "",
            "more_usable": "",
            "final_preference": "",
            "notes": "",
        })

    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"\n[저장 완료] {OUTPUT_PATH}")
    print(comparison_df)

    return comparison_df


# ============================================================
# 6. 메인 실행
# ============================================================
def main() -> None:
    compare_baseline_vs_rag()


if __name__ == "__main__":
    main()