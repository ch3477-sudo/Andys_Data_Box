# ============================================================
# - BM25 / Dense / RRF 기반 검색
# - response example 연결
# - example vector DB 기반 응답 예시 검색 추가
# - LLM으로 추천 답변 생성
# - 상황 요약 / 감정 / 위험도 / 추천 답변 / 피해야 할 표현 출력 강화
# ============================================================

from pathlib import Path
from collections import Counter, defaultdict
from typing import Any

import pandas as pd
try:
    from rank_bm25 import BM25Okapi
except ImportError as exc:
    raise ImportError(
        "rank_bm25 패키지가 설치되지 않았습니다. "
        "`pip install -r requirements.txt` 또는 `pip install rank-bm25`를 실행하세요."
    ) from exc

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate

try:
    from .api_key_loader import load_api_key
    from .pinecone_vector_store import (
        EXAMPLE_INDEX_NAME,
        RAG_INDEX_NAME,
        get_pinecone_vector_store,
    )
except ImportError:
    from api_key_loader import load_api_key
    from pinecone_vector_store import (
        EXAMPLE_INDEX_NAME,
        RAG_INDEX_NAME,
        get_pinecone_vector_store,
    )


# ============================================================
# 1. 경로 설정
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

RAG_TEXT_PATH = PROCESSED_DATA_DIR / "rag_documents_with_text.csv"
RESPONSE_TEXT_PATH = PROCESSED_DATA_DIR / "response_pairs_with_text.csv"
TARGET_RESPONSE_STYLES = ("공감형", "완화형", "비난 회피형")


# ============================================================
# 3. 유틸
# ============================================================
def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def infer_emotion_from_question(question: str) -> str:
    q = clean_text(question)

    if any(kw in q for kw in ["서운", "속상", "상처"]):
        return "슬픔"
    if any(kw in q for kw in ["화", "짜증", "무시", "열받"]):
        return "분노"
    if any(kw in q for kw in ["불안", "걱정"]):
        return "불안"
    if any(kw in q for kw in ["답답", "지쳐"]):
        return "답답함"
    return ""


def extract_keywords_from_question(question: str) -> list[str]:
    candidates = [
        "서운", "속상", "무시", "안 들어", "대충", "화", "상처",
        "답답", "공감", "진지", "읽씹", "답장", "회피", "장난", "집중",
        "연락", "말다툼", "반복", "지쳐"
    ]
    return [kw for kw in candidates if kw in question]


# ============================================================
# 4. 데이터/모델 로드
# ============================================================
def load_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not RAG_TEXT_PATH.exists():
        raise FileNotFoundError(f"파일이 없습니다: {RAG_TEXT_PATH}")
    if not RESPONSE_TEXT_PATH.exists():
        raise FileNotFoundError(f"파일이 없습니다: {RESPONSE_TEXT_PATH}")

    rag_df = pd.read_csv(RAG_TEXT_PATH)
    response_df = pd.read_csv(RESPONSE_TEXT_PATH)

    if "rag_text" not in rag_df.columns:
        raise ValueError("rag_df에 rag_text 컬럼이 없습니다.")

    rag_df["rag_text"] = rag_df["rag_text"].astype(str).str.strip()
    rag_df = rag_df[rag_df["rag_text"] != ""].copy()
    rag_df = rag_df.reset_index(drop=True)

    return rag_df, response_df


def build_bm25(rag_df: pd.DataFrame) -> BM25Okapi:
    rag_texts = rag_df["rag_text"].tolist()
    tokenized_rag_texts = [rag_text.split() for rag_text in rag_texts]
    return BM25Okapi(tokenized_rag_texts)


def load_vector_db(openai_api_key: str) -> Any:
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=openai_api_key,
    )

    vector_db = get_pinecone_vector_store(
        index_name=RAG_INDEX_NAME,
        embedding=embedding_model,
        pinecone_api_key=load_api_key("PINECONE_API_KEY"),
    )
    return vector_db


def load_example_vector_db(openai_api_key: str) -> Any:
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=openai_api_key,
    )

    example_vector_db = get_pinecone_vector_store(
        index_name=EXAMPLE_INDEX_NAME,
        embedding=embedding_model,
        pinecone_api_key=load_api_key("PINECONE_API_KEY"),
    )
    return example_vector_db


def load_llm(openai_api_key: str) -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0,
        api_key=openai_api_key,
    )


# ============================================================
# 5. 검색 함수
# ============================================================
def bm25_search(query: str, rag_df: pd.DataFrame, bm25: BM25Okapi, k: int = 3) -> list[dict]:
    tokenized_query = query.split()
    scores = bm25.get_scores(tokenized_query)

    result_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:k]

    results = []
    for idx in result_indices:
        row = rag_df.iloc[idx]
        results.append({
            "dialogue_id": clean_text(row.get("dialogue_id", "")),
            "relation": clean_text(row.get("relation", "")),
            "situation": clean_text(row.get("situation", "")),
            "speaker_emotion": clean_text(row.get("speaker_emotion", "")),
            "risk_level": clean_text(row.get("risk_level", "")),
            "page_content": clean_text(row.get("rag_text", "")),
        })
    return results


def dense_search(query: str, vector_db: Any, k: int = 3) -> list[dict]:
    retrieved_docs = vector_db.similarity_search(query, k=k)

    results = []
    for retrieved_doc in retrieved_docs:
        results.append({
            "dialogue_id": clean_text(retrieved_doc.metadata.get("dialogue_id", "")),
            "relation": clean_text(retrieved_doc.metadata.get("relation", "")),
            "situation": clean_text(retrieved_doc.metadata.get("situation", "")),
            "speaker_emotion": clean_text(retrieved_doc.metadata.get("speaker_emotion", "")),
            "risk_level": clean_text(retrieved_doc.metadata.get("risk_level", "")),
            "page_content": clean_text(retrieved_doc.page_content),
        })
    return results


def example_dense_search(question: str, example_vector_db: Any, k: int = 5) -> list[dict]:
    retrieved_examples = example_vector_db.similarity_search(question, k=k)

    results = []
    for retrieved_doc in retrieved_examples:
        results.append({
            "dialogue_id": clean_text(retrieved_doc.metadata.get("dialogue_id", "")),
            "relation": clean_text(retrieved_doc.metadata.get("relation", "")),
            "situation": clean_text(retrieved_doc.metadata.get("situation", "")),
            "speaker_emotion": clean_text(retrieved_doc.metadata.get("speaker_emotion", "")),
            "listener_empathy": clean_text(retrieved_doc.metadata.get("listener_empathy", "")),
            "terminate": clean_text(retrieved_doc.metadata.get("terminate", "")),
            "listener_response": clean_text(retrieved_doc.metadata.get("listener_response", "")),
            "response_example_text": clean_text(retrieved_doc.page_content),
        })
    return results


def reciprocal_rank_fusion(result_lists: list[list[dict]], k: int = 60, top_n: int = 3) -> list[dict]:
    fused_scores = defaultdict(float)
    item_lookup = {}

    for result_list in result_lists:
        for rank, item in enumerate(result_list, start=1):
            dialogue_id = item["dialogue_id"]
            if not dialogue_id:
                continue
            fused_scores[dialogue_id] += 1 / (k + rank)
            item_lookup[dialogue_id] = item

    ranked_ids = sorted(
        fused_scores.keys(),
        key=lambda x: fused_scores[x],
        reverse=True
    )[:top_n]

    return [item_lookup[dialogue_id] for dialogue_id in ranked_ids]


def retrieve_documents(
    question: str,
    rag_df: pd.DataFrame,
    bm25: BM25Okapi,
    vector_db: Any,
    method: str = "rrf",
    k: int = 3
) -> list[dict]:
    if method == "dense":
        return dense_search(question, vector_db=vector_db, k=k)

    if method == "bm25":
        return bm25_search(question, rag_df=rag_df, bm25=bm25, k=k)

    if method == "rrf":
        bm25_results = bm25_search(question, rag_df=rag_df, bm25=bm25, k=k)
        dense_results = dense_search(question, vector_db=vector_db, k=k)
        return reciprocal_rank_fusion([bm25_results, dense_results], top_n=k)

    raise ValueError("method는 'dense', 'bm25', 'rrf' 중 하나여야 합니다.")


# ============================================================
# 6. 감정 / 위험도 / 상황 요약
# ============================================================
def get_main_emotion(question: str, retrieved_docs: list[dict]) -> str:
    question_emotion = infer_emotion_from_question(question)
    if question_emotion:
        return question_emotion

    emotions = [
        clean_text(doc.get("speaker_emotion", ""))
        for doc in retrieved_docs
        if clean_text(doc.get("speaker_emotion", ""))
    ]

    if not emotions:
        return "미상"

    return Counter(emotions).most_common(1)[0][0]


def get_main_risk_level(retrieved_docs: list[dict]) -> str:
    risk_levels = [
        clean_text(doc.get("risk_level", ""))
        for doc in retrieved_docs
        if clean_text(doc.get("risk_level", ""))
    ]

    if not risk_levels:
        return "미상"

    normalized = []
    risk_map = {
        "낮음": "낮음",
        "보통": "보통",
        "중간": "보통",
        "높음": "높음",
    }

    for risk in risk_levels:
        normalized.append(risk_map.get(risk, risk))

    counter = Counter(normalized)
    return counter.most_common(1)[0][0]


def summarize_current_situation(question: str, retrieved_docs: list[dict]) -> str:
    if not retrieved_docs:
        return clean_text(question)

    top_doc = retrieved_docs[0]
    relation = clean_text(top_doc.get("relation", "연인"))
    situation = clean_text(top_doc.get("situation", ""))
    emotion = clean_text(top_doc.get("speaker_emotion", ""))

    parts = []
    if relation:
        parts.append(f"{relation} 관계에서")
    if situation:
        parts.append(situation)
    if emotion:
        parts.append(f"주된 감정은 {emotion}")

    if parts:
        return ", ".join(parts)

    return clean_text(question)


# ============================================================
# 7. response example 연결
# ============================================================
def filter_response_examples_by_dialogue_ids(response_df: pd.DataFrame, dialogue_ids: list[str]) -> pd.DataFrame:
    if "dialogue_id" not in response_df.columns:
        return response_df.copy()

    return response_df[
        response_df["dialogue_id"].astype(str).isin(dialogue_ids)
    ].copy()


def score_response_example(row: pd.Series, emotion: str, question_keywords: list[str]) -> int:
    score = 0

    relation = clean_text(row.get("relation", ""))
    situation = clean_text(row.get("situation", ""))
    speaker_emotion = clean_text(row.get("speaker_emotion", ""))
    context_before_response = clean_text(row.get("context_before_response", ""))
    listener_response = clean_text(row.get("listener_response", ""))
    listener_empathy = clean_text(row.get("listener_empathy", ""))
    response_example_text = clean_text(row.get("response_example_text", ""))

    merged_text = " ".join([
        relation,
        situation,
        speaker_emotion,
        context_before_response,
        listener_response,
        listener_empathy,
        response_example_text,
    ])

    if relation == "연인":
        score += 2

    if emotion and emotion in speaker_emotion:
        score += 3

    for kw in question_keywords:
        if kw in merged_text:
            score += 2

    if listener_empathy and listener_empathy != "미분류":
        score += 1

    if listener_response:
        score += 1

    return score


def map_listener_empathy_to_response_styles(listener_empathy: str) -> list[str]:
    empathy_text = clean_text(listener_empathy)
    if not empathy_text or empathy_text == "미분류":
        return []

    styles: list[str] = []
    if any(keyword in empathy_text for keyword in ["위로", "동조"]):
        styles.append("공감형")
    if any(keyword in empathy_text for keyword in ["조언", "격려"]):
        styles.append("완화형")
    if any(keyword in empathy_text for keyword in ["조언", "격려", "위로", "동조"]):
        styles.append("비난 회피형")
    return styles


def score_response_style_match(row: pd.Series, target_style: str) -> int:
    listener_empathy = clean_text(row.get("listener_empathy", ""))
    listener_response = clean_text(row.get("listener_response", ""))
    response_example_text = clean_text(row.get("response_example_text", ""))
    mapped_styles = map_listener_empathy_to_response_styles(listener_empathy)

    score = 0
    if target_style in mapped_styles:
        score += 10

    if target_style == "공감형":
        if any(keyword in listener_empathy for keyword in ["위로", "동조"]):
            score += 4
        if any(keyword in listener_response for keyword in ["서운", "힘들", "속상", "그랬겠다", "이해"]):
            score += 2

    elif target_style == "완화형":
        if any(keyword in listener_empathy for keyword in ["조언", "격려"]):
            score += 4
        if any(keyword in listener_response for keyword in ["천천히", "차분", "조금", "같이", "해보"]):
            score += 2

    elif target_style == "비난 회피형":
        if any(keyword in listener_empathy for keyword in ["조언", "격려", "위로", "동조"]):
            score += 3
        soft_text = " ".join([listener_response, response_example_text])
        if not any(keyword in soft_text for keyword in ["왜", "맨날", "항상", "네가", "니가", "잘못"]):
            score += 2

    return score


def _response_text_from_row(row: pd.Series) -> str:
    listener_response = clean_text(row.get("listener_response", ""))
    if listener_response:
        return listener_response
    return clean_text(row.get("response_example_text", ""))


def build_response_example_candidates(
    response_df: pd.DataFrame,
    retrieved_docs: list[dict],
    emotion: str,
    question: str,
    example_vector_db: Any,
) -> pd.DataFrame:
    dialogue_ids = [
        clean_text(doc.get("dialogue_id", ""))
        for doc in retrieved_docs
        if clean_text(doc.get("dialogue_id", ""))
    ]

    # 1차: 현재 검색된 문서와 직접 연결된 응답 예시
    candidate_df = filter_response_examples_by_dialogue_ids(response_df, dialogue_ids)

    # 2차: example vector DB에서 유사 응답 예시 검색
    vector_candidates = example_dense_search(question, example_vector_db, k=5)
    vector_candidate_df = pd.DataFrame(vector_candidates)

    # 두 후보 합치기
    if not vector_candidate_df.empty:
        if candidate_df.empty:
            candidate_df = vector_candidate_df.copy()
        else:
            merge_cols = [
                "dialogue_id",
                "relation",
                "situation",
                "speaker_emotion",
                "listener_empathy",
                "terminate",
                "listener_response",
                "response_example_text",
            ]

            for col in merge_cols:
                if col not in candidate_df.columns:
                    candidate_df[col] = ""

            candidate_df = pd.concat(
                [candidate_df[merge_cols], vector_candidate_df[merge_cols]],
                ignore_index=True
            )

            dedup_cols = ["dialogue_id", "listener_response"]
            candidate_df = candidate_df.drop_duplicates(subset=dedup_cols)

    # 그래도 비면 전체 fallback
    if candidate_df.empty:
        candidate_df = response_df.copy()

    question_keywords = extract_keywords_from_question(question)

    candidate_df["score"] = candidate_df.apply(
        lambda row: score_response_example(row, emotion, question_keywords),
        axis=1
    )

    return candidate_df.sort_values(by="score", ascending=False)


def select_style_labeled_response_examples(
    candidate_df: pd.DataFrame,
    target_styles: tuple[str, ...] = TARGET_RESPONSE_STYLES,
) -> list[dict]:
    if candidate_df.empty:
        return []

    selected: list[dict] = []
    used_keys: set[tuple[str, str]] = set()

    for target_style in target_styles:
        best_row = _select_best_response_row(candidate_df, target_style, used_keys)
        if best_row is None:
            continue

        text = _response_text_from_row(best_row)
        used_keys.add((clean_text(best_row.get("dialogue_id", "")), text))
        selected.append(
            {
                "label": target_style,
                "text": text,
                "source_listener_empathy": clean_text(best_row.get("listener_empathy", "")),
                "dialogue_id": clean_text(best_row.get("dialogue_id", "")),
            }
        )

    return selected


def _select_best_response_row(
    candidate_df: pd.DataFrame,
    target_style: str,
    used_keys: set[tuple[str, str]],
) -> pd.Series | None:
    best_row = None
    best_score = None

    for allow_reuse in [False, True]:
        for _, row in candidate_df.iterrows():
            text = _response_text_from_row(row)
            if not text:
                continue

            candidate_key = (
                clean_text(row.get("dialogue_id", "")),
                text,
            )
            if not allow_reuse and candidate_key in used_keys:
                continue

            style_score = score_response_style_match(row, target_style)
            total_score = int(row.get("score", 0)) + style_score
            if best_score is None or total_score > best_score:
                best_score = total_score
                best_row = row

        if best_row is None:
            continue
        return best_row

    return None


def format_labeled_response_examples(recommended_replies: list[dict]) -> str:
    return "\n\n".join(
        [
            f"[응답 예시 {index + 1} - {reply['label']}]\n{reply['text']}"
            for index, reply in enumerate(recommended_replies)
        ]
    )


def get_labeled_response_examples(
    response_df: pd.DataFrame,
    retrieved_docs: list[dict],
    emotion: str,
    question: str,
    example_vector_db: Any,
) -> list[dict]:
    candidate_df = build_response_example_candidates(
        response_df=response_df,
        retrieved_docs=retrieved_docs,
        emotion=emotion,
        question=question,
        example_vector_db=example_vector_db,
    )
    return select_style_labeled_response_examples(candidate_df)


def get_response_examples(
    response_df: pd.DataFrame,
    retrieved_docs: list[dict],
    emotion: str,
    question: str,
    example_vector_db: Any,
    top_n: int = 3
) -> str:
    recommended_replies = get_labeled_response_examples(
        response_df=response_df,
        retrieved_docs=retrieved_docs,
        emotion=emotion,
        question=question,
        example_vector_db=example_vector_db,
    )
    if recommended_replies:
        return format_labeled_response_examples(recommended_replies[:top_n])

    candidate_df = build_response_example_candidates(
        response_df=response_df,
        retrieved_docs=retrieved_docs,
        emotion=emotion,
        question=question,
        example_vector_db=example_vector_db,
    )
    text_col = "response_example_text" if "response_example_text" in candidate_df.columns else "listener_response"
    selected = candidate_df.head(top_n)[text_col].astype(str).tolist()

    return "\n\n".join(
        [f"[응답 예시 {i + 1}]\n{ex}" for i, ex in enumerate(selected)]
    )


def format_docs(docs: list[dict]) -> str:
    formatted = []

    for i, doc in enumerate(docs, start=1):
        block = [
            f"[유사 사례 {i}]",
            f"dialogue_id: {doc.get('dialogue_id', '')}",
            f"관계: {doc.get('relation', '')}",
            f"상황: {doc.get('situation', '')}",
            f"화자 감정: {doc.get('speaker_emotion', '')}",
            f"위험도: {doc.get('risk_level', '')}",
            f"본문 일부: {doc.get('page_content', '')[:500]}",
        ]
        formatted.append("\n".join(block))

    return "\n\n".join(formatted)


# ============================================================
# 8. 프롬프트
# ============================================================
PROMPT = PromptTemplate.from_template(
    """
너는 연인 갈등 상황에서 더 나은 답변을 추천하는 도우미다.

사용자가 연인과의 갈등 상황을 설명하면,
현재 상황 요약, 감정, 위험도, 추천 답변, 피해야 할 표현과 대체 표현을
이해하기 쉽게 정리해야 한다.

반드시 아래 조건을 지켜야 한다.
- 첫 문장에서 사용자의 감정을 분명하게 공감할 것
- 너무 길지 않게 작성할 것
- 답변은 2~4문장 정도로 작성할 것
- 공격적이거나 비난하는 말투는 피할 것
- 감정은 솔직하지만 부드럽게 전달할 것
- 실제 채팅에 바로 복붙해서 보낼 수 있는 문장으로 작성할 것
- 지나치게 상담사처럼 말하지 말 것
- 사용자의 현재 감정 톤을 반영할 것
- 유사 사례와 응답 예시는 참고만 하고, 그대로 복사하지 말 것
- 판단하거나 평가하지 말 것
- 해결책을 강요하지 말 것
- 필요하면 마지막에 짧은 질문 1개를 덧붙일 수 있음

사용자 입력:
{question}

상황 요약:
{situation_summary}

대표 감정:
{main_emotion}

갈등 위험도:
{risk_level}

유사 사례:
{context}

참고 응답 예시:
{response_examples}

아래 형식으로 출력할 것.

[상황 요약]
...

[감정]
...

[위험도]
...

[공감형]
...

[완화형]
...

[비난 회피형]
...

[피해야 할 표현]
...

[대체 표현]
...
"""
)


# ============================================================
# 9. 메인 생성 함수
# ============================================================
def generate_recommended_reply(question: str, method: str = "rrf", k: int = 3) -> dict:
    openai_api_key = load_api_key()
    rag_df, response_df = load_dataframes()
    bm25 = build_bm25(rag_df)
    vector_db = load_vector_db(openai_api_key)
    example_vector_db = load_example_vector_db(openai_api_key)
    chat_model = load_llm(openai_api_key)

    retrieved_docs = retrieve_documents(
        question=question,
        rag_df=rag_df,
        bm25=bm25,
        vector_db=vector_db,
        method=method,
        k=k,
    )

    situation_summary = summarize_current_situation(question, retrieved_docs)
    main_emotion = get_main_emotion(question, retrieved_docs)
    risk_level = get_main_risk_level(retrieved_docs)
    context = format_docs(retrieved_docs)

    recommended_replies = get_labeled_response_examples(
        response_df=response_df,
        retrieved_docs=retrieved_docs,
        emotion=main_emotion,
        question=question,
        example_vector_db=example_vector_db,
    )
    response_examples = format_labeled_response_examples(recommended_replies)

    final_prompt = PROMPT.format(
        question=question,
        situation_summary=situation_summary,
        main_emotion=main_emotion,
        risk_level=risk_level,
        context=context,
        response_examples=response_examples,
    )

    llm_response = chat_model.invoke(final_prompt)

    return {
        "question": question,
        "method": method,
        "retrieved_docs": retrieved_docs,
        "situation_summary": situation_summary,
        "main_emotion": main_emotion,
        "risk_level": risk_level,
        "response_examples": response_examples,
        "recommended_replies": recommended_replies,
        "result_text": llm_response.content,
    }


# ============================================================
# 10. 단독 실행 테스트
# ============================================================
def main() -> None:
    test_question = "남자친구가 내 말을 제대로 안 들어주는 것 같아서 서운해. 어떻게 보내면 좋을까?"
    output = generate_recommended_reply(test_question, method="rrf", k=3)

    print("\n===== 입력 질문 =====")
    print(output["question"])

    print("\n===== 검색된 유사 사례 수 =====")
    print(len(output["retrieved_docs"]))

    print("\n===== 상황 요약 =====")
    print(output["situation_summary"])

    print("\n===== 대표 감정 =====")
    print(output["main_emotion"])

    print("\n===== 갈등 위험도 =====")
    print(output["risk_level"])

    print("\n===== 응답 예시 =====")
    print(output["response_examples"])

    print("\n===== 최종 생성 결과 =====")
    print(output["result_text"])


if __name__ == "__main__":
    main()
