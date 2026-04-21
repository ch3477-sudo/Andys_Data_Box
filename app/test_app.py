import sys
from pathlib import Path
import streamlit as st

# 프로젝트 루트를 import 경로에 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# 이미지 분석 함수 제외
from src.app_service import run_chat_analysis

st.set_page_config(page_title="연인 갈등 대응 AI", layout="wide")

def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Noto Sans KR', sans-serif;
            background-color: #F8F9FA;
        }

        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 25px;
            background: #FFF0F3;
            border-bottom: 1px solid #eee;
            margin-bottom: 20px;
            border-radius: 12px;
        }

        .top-bar strong {
            font-size: 24px;
            color: #212529;
            font-weight: 700;
        }

        .section-title {
            font-size: 18px;
            font-weight: 700;
            color: #212529;
            margin-bottom: 12px;
        }

        .message-row {
            width: 100%;
            clear: both;
            margin-bottom: 20px;
            display: flex;
            align-items: flex-start;
        }

        .row-right {
            flex-direction: row-reverse;
        }

        .bubble {
            max-width: 78%;
            padding: 12px 18px;
            border-radius: 15px;
            font-size: 14px;
            line-height: 1.65;
            background: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
            white-space: pre-wrap;
        }

        .bubble-left {
            border: 1px solid #DEE2E6;
        }

        .bubble-right {
            border: 2px solid #916848;
            background: #FFFDF9;
        }

        .avatar {
            font-size: 25px;
            margin: 0 12px;
        }

        .card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            text-align: center;
            border: 1px solid #f0f0f0;
            min-height: 180px;
        }

        .gauge-container {
            background: #E9ECEF;
            border-radius: 10px;
            height: 8px;
            width: 100%;
            margin-top: 10px;
        }

        .gauge-fill {
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease-in-out;
        }

        .list-item {
            display: flex;
            align-items: flex-start;
            padding: 12px;
            background: white;
            border-radius: 12px;
            margin-bottom: 10px;
            border: 1px solid #eee;
            position: relative;
        }

        .item-icon {
            background: #EDF2FF;
            color: #4C6EF5;
            width: 38px;
            height: 38px;
            display: flex;
            justify-content: center;
            align-items: center;
            border-radius: 10px;
            font-weight: 700;
            flex-shrink: 0;
        }

        .item-content {
            flex: 1;
            margin-left: 12px;
            font-size: 13.5px;
            line-height: 1.6;
            color: #333;
            padding-right: 50px;
        }

        /* 복사 버튼 스타일 */
        .copy-button {
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            background: #f1f3f5;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            cursor: pointer;
            color: #495057;
            transition: all 0.2s;
        }

        .copy-button:hover {
            background: #e9ecef;
            border-color: #ced4da;
        }

        .active-history {
            background: #EDF2FF;
            border-color: #DBE4FF;
        }

        .sub-card {
            background: white;
            border: 1px solid #eee;
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 10px;
        }

        .small-label {
            font-size: 12px;
            color: #888;
            margin-bottom: 6px;
        }

        .pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #F1F3F5;
            color: #666;
            font-size: 11px;
            margin-bottom: 10px;
        }

        .note-box {
            background: #FFFFFF;
            border: 1px dashed #D0D7DE;
            border-radius: 12px;
            padding: 12px 14px;
            font-size: 13px;
            color: #555;
            line-height: 1.6;
        }
        </style>

        <script>
        function copyToClipboard(text) {
            const tempTextArea = document.createElement('textarea');
            tempTextArea.value = text.replace(/<br>/g, '\\n');
            document.body.appendChild(tempTextArea);
            tempTextArea.select();
            document.execCommand('copy');
            document.body.removeChild(tempTextArea);
            alert('답변이 클립보드에 복사되었습니다.');
        }
        </script>
    """, unsafe_allow_html=True)


def clean_display_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip().strip('"').strip("'")
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    return text


def render_analysis_card(title: str, emoji: str, label: str, score: int, color: str, description: str = ""):
    safe_label = clean_display_text(label)
    safe_desc = clean_display_text(description)

    st.markdown(f"""
        <div class="card">
            <div style="color:#888; font-size:13px;">{title}</div>
            <div style="font-size:45px; margin:10px 0;">{emoji}</div>
            <div style="font-weight:700; font-size:20px; color:{color if title == '위험도 분석' else '#212529'};">
                {safe_label}
            </div>
            <div style="font-size:12px; color:{color}; margin-top:5px;">신뢰도 {score}%</div>
            <div class="gauge-container">
                <div class="gauge-fill" style="width:{score}%; background:{color};"></div>
            </div>
            <div style="font-size:12px; color:#868E96; margin-top:10px; line-height:1.5;">
                {safe_desc}
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_history_item(icon: str, title: str, time_text: str, preview: str, is_active: bool = False):
    active_cls = "active-history" if is_active else ""
    title_color = "#4C6EF5" if is_active else "#333"
    title = clean_display_text(title)
    preview = clean_display_text(preview)

    st.markdown(f"""
        <div class="list-item {active_cls}">
            <div style="font-size:24px;">{icon}</div>
            <div class="item-content">
                <div style="display:flex; justify-content:space-between; gap:8px;">
                    <span style="font-weight:700; color:{title_color};">{title}</span>
                    <span style="font-size:11px; color:#aaa; white-space:nowrap;">{time_text}</span>
                </div>
                <div style="font-size:12px; color:#888; margin-top:2px;">{preview}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_text_box(title: str, body: str):
    body = clean_display_text(body)
    st.markdown(
        f"""
        <div class="sub-card">
            <div class="small-label">{title}</div>
            <div style="font-size:13.5px; line-height:1.65; color:#333;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_phrase_box(title: str, items: list[str], empty_text: str):
    if not items:
        render_text_box(title, empty_text)
        return

    for item in items:
        item = clean_display_text(item)
        render_text_box(title, item)


def get_risk_color(label: str) -> str:
    label = clean_display_text(label)
    if label in ["심각", "위험"]:
        return "#E74C3C"
    if label in ["경고", "주의", "보통"]:
        return "#F08C00"
    return "#5C7CFA"


def get_emotion_emoji(label: str) -> str:
    label = clean_display_text(label)
    mapping = {
        "분노": "😡", "슬픔": "😢", "혐오": "😖", "공포": "😨", "행복": "😊",
        "놀람": "😮", "중립": "😐", "상처": "😢", "불안": "😟", "서운함": "😢", "미분석": "🙂",
    }
    return mapping.get(label, "🙂")


def get_risk_description(label: str) -> str:
    label = clean_display_text(label)
    mapping = {
        "안전": "감정이 크게 격화된 상태는 아닙니다.",
        "주의": "표현 방식에 따라 갈등이 커질 수 있습니다.",
        "경고": "감정 충돌 가능성이 있어 부드러운 표현이 중요합니다.",
        "위험": "자극적인 표현을 피하고 감정 진정이 우선입니다.",
        "심각": "즉각적인 설득보다 상황 진정이 더 중요합니다.",
        "보통": "표현을 조심하면 충분히 대화를 이어갈 수 있습니다.",
        "미분석": "분석 결과를 기다리는 중입니다.",
    }
    return mapping.get(label, "현재 대화 흐름을 조심스럽게 이어가는 것이 좋습니다.")


def get_emotion_description(label: str) -> str:
    label = clean_display_text(label)
    mapping = {
        "분노": "억울함이나 답답함이 함께 섞여 있을 수 있습니다.",
        "슬픔": "서운함, 상처, 외로움이 함께 나타날 수 있습니다.",
        "중립": "감정이 비교적 안정적인 상태입니다.",
        "상처": "정서적으로 마음이 상한 상태에 가깝습니다.",
        "불안": "관계 변화나 반응에 대한 걱정이 섞여 있을 수 있습니다.",
        "서운함": "기대와 다른 반응에서 오는 아쉬움이 큽니다.",
    }
    return mapping.get(label, "현재 감정 흐름을 참고해 대화를 조절하는 것이 좋습니다.")


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "avatar": "🐰", "content": "안녕. 고민되는 상황이나 상대방의 메시지를 입력해줘. 감정 분석과 대응 답변을 알려줄게."}
        ]
    if "latest_result" not in st.session_state:
        st.session_state.latest_result = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "error_message" not in st.session_state:
        st.session_state.error_message = ""


def main():
    apply_custom_css()
    init_session_state()

    st.markdown(
        '<div class="top-bar"><strong>🎁 연인 갈등 상황 대응 답변 추천 AI</strong><span>⛶</span></div>',
        unsafe_allow_html=True
    )

    col_chat, col_report = st.columns([5.5, 4.5])

    with col_chat:
        st.markdown(
            '<div style="display:flex; justify-content:space-between; padding:0 10px 10px;"><span>〈 22</span><strong>Andy</strong><span>🔍 ☰</span></div>',
            unsafe_allow_html=True
        )

        with st.container(height=550):
            st.markdown(
                '<div style="text-align:center; margin-bottom:20px;"><span class="pill">📅 2026.04.27</span></div>',
                unsafe_allow_html=True
            )

            for msg in st.session_state.messages:
                is_user = msg["role"] == "user"
                avatar = "🐶" if is_user else msg.get("avatar", "🐰")
                bubble_class = "bubble-right" if is_user else "bubble-left"
                row_class = "row-right" if is_user else ""
                content = clean_display_text(msg["content"]).replace("\n", "<br>")

                st.markdown(
                    f"""
                    <div class="message-row {row_class}">
                        <div class="avatar">{avatar}</div>
                        <div class="bubble {bubble_class}">{content}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        if prompt := st.chat_input("상황이나 대화 내용을 입력하세요..."):
            st.session_state.error_message = ""
            st.session_state.messages.append({"role": "user", "content": prompt})

            try:
                with st.spinner("분석 중..."):
                    result = run_chat_analysis(prompt)

                st.session_state.latest_result = result
                st.session_state.messages.append(
                    {"role": "assistant", "avatar": "🐰", "content": clean_display_text(result["assistant_message"])}
                )
                st.session_state.history.insert(0, result)
            except Exception as e:
                st.session_state.error_message = str(e)
                st.session_state.messages.append(
                    {"role": "assistant", "avatar": "🐰", "content": "분석 중 오류가 발생했어. 설정을 확인해줘."}
                )
            st.rerun()

    with col_report:
        st.markdown('<div class="section-title">AI 분석 결과</div>', unsafe_allow_html=True)

        latest = st.session_state.latest_result
        emotion_label, emotion_score, emotion_emoji, emotion_desc = "대기 중", 0, "🙂", "입력 시 분석을 시작합니다."
        risk_label, risk_score, risk_color, risk_desc = "대기 중", 0, "#ADB5BD", "갈등 위험도를 측정합니다."

        if latest:
            emotion_label = clean_display_text(latest["emotion"]["label"])
            emotion_score = latest["emotion"]["score"]
            emotion_emoji = get_emotion_emoji(emotion_label)
            emotion_desc = get_emotion_description(emotion_label)
            risk_label = clean_display_text(latest["risk"]["label"])
            risk_score = latest["risk"]["score"]
            risk_color = get_risk_color(risk_label)
            risk_desc = get_risk_description(risk_label)

        card_l, card_r = st.columns(2)
        with card_l:
            render_analysis_card("감정 분석", emotion_emoji, emotion_label, emotion_score, "#5C7CFA", emotion_desc)
        with card_r:
            render_analysis_card("위험도 분석", "⏱️", risk_label, risk_score, risk_color, risk_desc)

        if st.session_state.error_message:
            st.error(st.session_state.error_message)

        st.write("")
        st.markdown("<strong>입력 메시지 분석</strong>", unsafe_allow_html=True)

        if latest:
            render_text_box("상황 요약", latest.get("summary_text", ""))
            render_text_box("감정 해석", latest.get("emotion_text", ""))
            if latest["risk"].get("recommendation"):
                render_text_box("대응 가이드", latest["risk"]["recommendation"])
        else:
            st.markdown('<div class="note-box">왼쪽 대화창에 내용을 입력하면 상세 분석 결과가 표시됩니다.</div>', unsafe_allow_html=True)

        st.write("")
        st.markdown(
            "<div style='display:flex; justify-content:space-between; align-items:center;'><strong>💡 AI 추천 답변</strong><span style='font-size:12px; color:#aaa;'>복사</span></div>",
            unsafe_allow_html=True
        )

        if latest and latest.get("reply_candidates"):
            for i, text in enumerate(latest["reply_candidates"][:3], 1):
                safe_text = clean_display_text(text).replace("\n", "<br>")

                st.markdown(
                    f"""
                    <div class="list-item">
                        <div class="item-icon">{i}</div>
                        <div class="item-content">{safe_text}</div>
                        <button class="copy-button"
                        onclick='copyToClipboard(`{safe_text}`)'>복사</button>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("분석 후 추천 답변이 표시됩니다.")

        if latest and latest.get("recommended_replies"):
            st.write("")
            st.markdown("<strong>📚 RAG 참고 예시</strong>", unsafe_allow_html=True)
            for item in latest["recommended_replies"][:3]:
                label = clean_display_text(item.get("label", ""))
                text = clean_display_text(item.get("text", ""))
                source = clean_display_text(item.get("source_listener_empathy", ""))
                evidence = f"[{label}] {text}"
                if source:
                    evidence += f"\n근거 유형: {source}"
                render_text_box("검색된 응답 예시", evidence)

        st.write("")
        st.markdown("<strong>⚠️ 피해야 할 표현 / 대체 표현</strong>", unsafe_allow_html=True)
        l_col, r_col = st.columns(2)
        if latest:
            with l_col: render_phrase_box("피해야 할 표현", [clean_display_text(x) for x in latest.get("avoid_phrases", [])][:2], "없음")
            with r_col: render_phrase_box("대체 표현", [clean_display_text(x) for x in latest.get("alternative_phrases", [])][:2], "없음")
        else:
            with l_col: render_text_box("피해야 할 표현", "예: 비난형 표현")
            with r_col: render_text_box("대체 표현", "예: 감정 설명형 표현")

        st.write("")
        st.markdown("<strong>대화 히스토리 (최근 3개)</strong>", unsafe_allow_html=True)
        if st.session_state.history:
            for idx, item in enumerate(st.session_state.history[:3]):
                render_history_item("💬", item.get("user_input", "")[:30], "방금" if idx==0 else f"{idx+1}전", item.get("assistant_message", "")[:70], idx==0)
        else:
            render_history_item("💬", "히스토리 없음", "-", "첫 분석을 시작해보세요.", True)

if __name__ == "__main__":
    main()
