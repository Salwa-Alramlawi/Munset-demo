"""Munset — Streamlit UI for the judicial transcription multi-agent system."""

import os
import json
import tempfile
import streamlit as st
from session_store import SessionStore

# ---- Page config ----
st.set_page_config(
    page_title="مُنصِت | توثيق الجلسات القضائية",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- RTL & Custom CSS ----
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');

    * { font-family: 'Tajawal', sans-serif; }
    html, body, .stApp { direction: rtl; }
    .main .block-container { direction: rtl; text-align: right; }

    /* Force RTL on all Streamlit elements */
    .stMarkdown, .stText, .stAlert, .stJson,
    .stTextInput > div, .stTextArea > div,
    .stSelectbox > div, .stMultiSelect > div,
    .stFileUploader > div, .stChatMessage,
    [data-testid="stChatInput"], [data-testid="stChatMessage"],
    .stTabs [data-baseweb="tab"], .stExpander,
    h1, h2, h3, h4, h5, h6, p, li, td, th, label, span {
        direction: rtl !important;
        text-align: right !important;
    }

    /* Sidebar RTL */
    [data-testid="stSidebar"] { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] .stMarkdown { direction: rtl !important; text-align: right !important; }

    /* Tabs RTL */
    .stTabs [data-baseweb="tab-list"] { direction: rtl; flex-direction: row-reverse; }

    /* Buttons alignment */
    .stButton > button { direction: rtl; }

    /* Chat messages RTL */
    [data-testid="stChatMessage"] > div { direction: rtl !important; text-align: right !important; }
    .stChatInputContainer { direction: rtl; }
    [data-testid="stChatInput"] textarea { direction: rtl; text-align: right; }

    /* Tables RTL */
    table { direction: rtl; }
    th, td { text-align: right !important; }

    /* Progress bar */
    .stProgress > div { direction: ltr; }

    /* File uploader */
    [data-testid="stFileUploader"] { direction: rtl; }

    .agent-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        color: #e2e8f0;
    }
    .agent-card h4 { color: #38bdf8; margin: 0 0 0.5rem 0; }
    .agent-active { border-color: #22d3ee; box-shadow: 0 0 15px rgba(34,211,238,0.3); }
    .agent-done { border-color: #22c55e; }

    .a2a-arrow {
        text-align: center;
        font-size: 1.5rem;
        color: #22d3ee;
        padding: 0.3rem;
    }

    .metric-box {
        background: #1e293b;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #334155;
    }
    .metric-box .number { font-size: 2rem; font-weight: 700; color: #22d3ee; }
    .metric-box .label { color: #94a3b8; font-size: 0.85rem; }

    .chat-user {
        background: #1e3a5f; border-radius: 12px; padding: 0.8rem 1rem;
        margin: 0.5rem 0; margin-left: 20%;
    }
    .chat-bot {
        background: #1e293b; border-radius: 12px; padding: 0.8rem 1rem;
        margin: 0.5rem 0; margin-right: 20%; border: 1px solid #334155;
    }

    /* Agent flow animation */
    @keyframes pulseGlow {
        0% { box-shadow: 0 0 5px rgba(34,211,238,0.3); }
        50% { box-shadow: 0 0 20px rgba(34,211,238,0.6); }
        100% { box-shadow: 0 0 5px rgba(34,211,238,0.3); }
    }
    .agent-flow-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 0.8rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    .agent-flow-card:hover {
        border-color: #22d3ee;
        animation: pulseGlow 2s infinite;
        transform: translateY(-2px);
    }
    .agent-flow-card .icon { font-size: 1.8rem; }
    .agent-flow-card .name { color: #22d3ee; font-size: 0.8rem; font-weight: 700; margin-top: 0.3rem; }
    .agent-flow-card .tech { color: #64748b; font-size: 0.65rem; }

    .flow-arrow {
        color: #22d3ee;
        font-size: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
    }
    .flow-arrow-back {
        color: #f97316;
        font-size: 1rem;
    }

    /* Demo badge */
    .demo-badge {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 1rem;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # ---- Sidebar ----
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/law.png", width=60)
        st.markdown("# ⚖️ مُنصِت")
        st.markdown("**منظومة وكلاء ذكية لتوثيق الجلسات القضائية**")
        st.divider()

        st.markdown("### الوكلاء")
        agents_info = [
            ("🎙️", "وكيل التفريغ الصوتي", "Whisper + Speaker Diarization"),
            ("⚖️", "وكيل التحليل القانوني", "استخراج الادعاءات والدفوع"),
            ("📝", "وكيل التلخيص", "محضر جلسة مُهيكل"),
            ("✅", "وكيل المراجعة", "ضبط الجودة والاكتمال"),
            ("💬", "المساعد التفاعلي", "سؤال وجواب على المحضر"),
        ]
        for icon, name, desc in agents_info:
            st.markdown(f"**{icon} {name}**  \n{desc}")

        st.divider()
        st.markdown("### تخصيص المتحدثين")
        speaker_map = {}
        default_labels = ["القاضي", "المدعي", "المدعى عليه", "محامي المدعي", "محامي المدعى عليه"]
        for i, default in enumerate(default_labels):
            label = st.text_input(f"المتحدث {i+1}", value=default, key=f"spk_{i}")
            speaker_map[f"SPEAKER_{i:02d}"] = label

    # ---- Main Area ----
    st.markdown("# ⚖️ مُنصِت")
    st.markdown("### منظومة وكلاء ذكية لتوثيق وتحليل الجلسات القضائية")
    st.markdown("---")

    # ---- Mode Selection ----
    st.markdown("### اختر وضع التشغيل")
    mode_col1, mode_col2 = st.columns(2)

    with mode_col1:
        demo_clicked = st.button(
            "🎬 تشغيل العرض التجريبي (Demo)",
            type="primary",
            use_container_width=True,
            help="عرض تجريبي بجلسة محضّرة مسبقاً — لا يحتاج GPU أو مفاتيح API",
        )

    with mode_col2:
        st.markdown(
            "<div style='background:#1e293b; padding:0.8rem; border-radius:8px; "
            "text-align:center; color:#94a3b8; font-size:0.9rem;'>"
            "أو ارفع تسجيل صوتي حقيقي ↓</div>",
            unsafe_allow_html=True,
        )

    # ---- Demo Mode ----
    if demo_clicked:
        from pipeline import MunsetPipeline

        pipeline = MunsetPipeline()
        progress = st.progress(0, text="جاري تجهيز العرض التجريبي...")

        def on_step(name, step, total):
            progress.progress(step / total, text=f"⏳ {name}...")

        with st.spinner("الوكلاء يعملون..."):
            results = pipeline.run_demo(on_step=on_step)

        progress.progress(1.0, text="✅ اكتمل التحليل!")
        st.session_state["results"] = results
        st.session_state["pipeline"] = pipeline

    st.markdown("---")

    # ---- Upload ----
    uploaded = st.file_uploader(
        "📁 ارفع التسجيل الصوتي للجلسة",
        type=["mp3", "wav", "m4a", "ogg", "flac", "mp4"],
        help="يدعم: MP3, WAV, M4A, OGG, FLAC, MP4",
    )

    if uploaded is not None:
        st.audio(uploaded)

        if st.button("🚀 ابدأ التحليل", type="primary", use_container_width=True):
            # Save uploaded file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1])
            tmp.write(uploaded.read())
            tmp.close()

            from pipeline import MunsetPipeline

            pipeline = MunsetPipeline()
            progress = st.progress(0, text="جاري التجهيز...")

            def on_step(name, step, total):
                progress.progress(step / total, text=f"⏳ {name}...")

            with st.spinner("الوكلاء يعملون..."):
                results = pipeline.run(tmp.name, speaker_map=speaker_map, on_step=on_step)

            progress.progress(1.0, text="✅ اكتمل التحليل!")
            st.session_state["results"] = results
            st.session_state["pipeline"] = pipeline

            # Cleanup
            os.unlink(tmp.name)

    # ---- Results ----
    if "results" in st.session_state:
        results = st.session_state["results"]

        # Demo mode badge
        if results.get("demo_mode"):
            st.markdown('<span class="demo-badge">وضع العرض التجريبي</span>', unsafe_allow_html=True)

        # Agent flow visualization
        st.markdown("### 🔄 مسار تدفق الوكلاء (A2A)")
        st.markdown("<p style='color:#94a3b8; font-size:0.85rem;'>الأسهم الزرقاء = تدفق البيانات للأمام | الأسهم البرتقالية = ملاحظات الجودة والتوضيحات (ثنائي الاتجاه)</p>", unsafe_allow_html=True)

        flow_cols = st.columns([2, 1, 2, 1, 2, 1, 2, 1, 2])
        agents_flow = [
            ("🎙️", "التفريغ الصوتي", "Whisper + pyannote"),
            None,
            ("⚖️", "التحليل القانوني", "Claude API"),
            None,
            ("📝", "التلخيص", "Claude API"),
            None,
            ("✅", "مراجعة الجودة", "Claude API"),
            None,
            ("💬", "المساعد التفاعلي", "Claude API"),
        ]
        for i, col in enumerate(flow_cols):
            with col:
                if agents_flow[i] is not None:
                    icon, name, tech = agents_flow[i]
                    st.markdown(
                        f"<div class='agent-flow-card'>"
                        f"<div class='icon'>{icon}</div>"
                        f"<div class='name'>{name}</div>"
                        f"<div class='tech'>{tech}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div class='flow-arrow'>→</div>",
                        unsafe_allow_html=True,
                    )

        # Feedback arrows (backward)
        st.markdown(
            "<div style='text-align:center; padding:0.3rem; color:#f97316; font-size:0.8rem;'>"
            "← ← ← ← ملاحظات الجودة والتوضيحات (وكيل المراجعة ← وكيل التلخيص / وكيل التحليل) ← ← ← ←"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Tabs for results
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🎙️ التفريغ الصوتي",
            "⚖️ التحليل القانوني",
            "📝 محضر الجلسة",
            "✅ تقرير الجودة",
            "💬 المساعد التفاعلي",
            "🔗 سجل A2A",
            "📂 الجلسات السابقة",
        ])

        # -- Tab 1: Transcription --
        with tab1:
            st.markdown("### النص المُفرّغ مع تحديد المتحدثين")
            transcript_data = results.get("transcription", {})
            segments = transcript_data.get("segments", [])

            if segments:
                for seg in segments:
                    speaker_color = {
                        "القاضي": "#f59e0b",
                        "المدعي": "#3b82f6",
                        "المدعى عليه": "#ef4444",
                    }.get(seg["speaker"], "#94a3b8")

                    st.markdown(
                        f"<div style='padding:0.5rem; margin:0.3rem 0; "
                        f"border-right: 3px solid {speaker_color}; "
                        f"background: #1e293b; border-radius: 6px;'>"
                        f"<strong style='color:{speaker_color}'>{seg['speaker']}</strong> "
                        f"<span style='color:#64748b; font-size:0.8rem'>"
                        f"[{seg['start']:.1f}s - {seg['end']:.1f}s]</span><br/>"
                        f"{seg['text']}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.text(transcript_data.get("full_transcript", ""))

        # -- Tab 2: Legal Analysis --
        with tab2:
            st.markdown("### التحليل القانوني المُهيكل")
            analysis = results.get("legal_analysis", {})

            if not analysis.get("parse_error"):
                col_a, col_b = st.columns(2)

                with col_a:
                    st.markdown("**📋 نوع القضية:**")
                    st.info(analysis.get("case_type", "غير محدد"))

                    st.markdown("**🔴 الادعاءات:**")
                    for c in analysis.get("claims", []):
                        st.markdown(f"- {c}")

                    st.markdown("**🟢 الدفوع:**")
                    for d in analysis.get("defenses", []):
                        st.markdown(f"- {d}")

                    st.markdown("**📎 الأدلة:**")
                    for e in analysis.get("evidence", []):
                        st.markdown(f"- {e}")

                with col_b:
                    st.markdown("**📖 المواد النظامية:**")
                    for a in analysis.get("legal_articles", []):
                        st.markdown(f"- {a}")

                    st.markdown("**📌 طلبات المدعي:**")
                    for r in analysis.get("requests", {}).get("plaintiff", []):
                        st.markdown(f"- {r}")

                    st.markdown("**📌 طلبات المدعى عليه:**")
                    for r in analysis.get("requests", {}).get("defendant", []):
                        st.markdown(f"- {r}")

                    if analysis.get("contradictions"):
                        st.markdown("**⚠️ تناقضات:**")
                        for x in analysis["contradictions"]:
                            st.warning(x)
            else:
                st.json(analysis)

        # -- Tab 3: Summary --
        with tab3:
            st.markdown("### محضر الجلسة والملخص التنفيذي")
            st.markdown(results.get("summary", ""))

        # -- Tab 4: QA Review --
        with tab4:
            st.markdown("### تقرير مراجعة الجودة")
            qa = results.get("qa_review", {})

            if not qa.get("parse_error"):
                score = qa.get("completeness_score", 0)
                st.markdown(
                    f"<div class='metric-box'>"
                    f"<div class='number'>{score}%</div>"
                    f"<div class='label'>نسبة اكتمال المحضر</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.progress(score / 100)

                st.markdown("**📝 التقييم العام:**")
                st.info(qa.get("overall_assessment", ""))

                issues = qa.get("issues", [])
                if issues:
                    st.markdown("**🔍 الملاحظات:**")
                    for issue in issues:
                        severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                            issue.get("severity", ""), "⚪"
                        )
                        st.markdown(f"{severity_icon} **{issue.get('type', '')}**: {issue.get('description', '')}")
                else:
                    st.success("لا توجد ملاحظات — المحضر مكتمل ودقيق.")
            else:
                st.json(qa)

        # -- Tab 5: Chatbot --
        with tab5:
            st.markdown("### 💬 اسأل عن الجلسة")
            st.markdown("يمكنك سؤال المساعد الذكي عن أي تفصيل في الجلسة")

            # Initialize chat history
            if "chat_messages" not in st.session_state:
                st.session_state["chat_messages"] = []

            # Display chat history
            for msg in st.session_state["chat_messages"]:
                css_class = "chat-user" if msg["role"] == "user" else "chat-bot"
                prefix = "👤" if msg["role"] == "user" else "🤖"
                st.markdown(
                    f"<div class='{css_class}'>{prefix} {msg['content']}</div>",
                    unsafe_allow_html=True,
                )

            # Quick questions
            st.markdown("**أسئلة سريعة:**")
            quick_qs = [
                "ما هي طلبات المدعي؟",
                "ما موقف المدعى عليه؟",
                "ما المواد النظامية المذكورة؟",
                "لخّص لي الجلسة في 3 أسطر",
            ]
            cols_q = st.columns(len(quick_qs))
            selected_q = None
            for i, q in enumerate(quick_qs):
                if cols_q[i].button(q, key=f"quick_{i}"):
                    selected_q = q

            user_input = st.chat_input("اكتب سؤالك هنا...")
            question = selected_q or user_input

            if question and "pipeline" in st.session_state:
                st.session_state["chat_messages"].append({"role": "user", "content": question})

                with st.spinner("جاري الإجابة..."):
                    answer = st.session_state["pipeline"].ask_chatbot(question)

                st.session_state["chat_messages"].append({"role": "assistant", "content": answer})
                st.rerun()

        # -- Tab 6: A2A Log --
        with tab6:
            st.markdown("### 🔗 سجل تواصل الوكلاء (A2A Protocol)")
            st.markdown("يوضح كيف تتواصل الوكلاء مع بعضها عبر بروتوكول A2A — بما في ذلك التواصل الثنائي (Feedback & Clarification)")

            # A2A Stats
            stats = results.get("a2a_stats", {})
            if stats:
                st.markdown("#### 📊 إحصائيات التواصل بين الوكلاء")
                stat_cols = st.columns(len(stats))
                agent_labels = {
                    "pipeline": "المنسّق",
                    "transcription_agent": "التفريغ",
                    "legal_analysis_agent": "التحليل",
                    "summary_agent": "التلخيص",
                    "qa_agent": "المراجعة",
                    "chatbot_agent": "الشات بوت",
                    "user": "المستخدم",
                }
                for i, (agent, data) in enumerate(stats.items()):
                    if i < len(stat_cols):
                        with stat_cols[i]:
                            label = agent_labels.get(agent, agent)
                            st.markdown(
                                f"<div class='metric-box'>"
                                f"<div class='number' style='font-size:1.2rem'>{data['sent'] + data['received']}</div>"
                                f"<div class='label'>{label}</div>"
                                f"<div style='font-size:0.7rem; color:#64748b;'>"
                                f"↑{data['sent']} ↓{data['received']}"
                                f"{' 🔄' + str(data['clarifications']) if data.get('clarifications') else ''}"
                                f"{' 💬' + str(data['feedbacks']) if data.get('feedbacks') else ''}"
                                f"</div></div>",
                                unsafe_allow_html=True,
                            )
                st.markdown("---")

            # Message Log
            log = results.get("a2a_log", [])
            for entry in log:
                sender = entry.get("sender", "")
                receiver = entry.get("receiver", "")
                msg_type = entry.get("msg_type", "")
                timestamp = entry.get("timestamp", "")
                priority = entry.get("priority", "normal")

                type_color = {
                    "data": "#3b82f6",
                    "response": "#22c55e",
                    "request": "#f59e0b",
                    "clarification_request": "#a855f7",
                    "clarification_response": "#8b5cf6",
                    "feedback": "#f97316",
                }.get(msg_type, "#94a3b8")

                type_label = {
                    "data": "بيانات",
                    "response": "استجابة",
                    "request": "طلب",
                    "clarification_request": "🔄 طلب توضيح",
                    "clarification_response": "🔄 رد توضيح",
                    "feedback": "💬 ملاحظة جودة",
                }.get(msg_type, msg_type)

                priority_badge = ""
                if priority == "high":
                    priority_badge = " <span style='background:#ef4444; color:#fff; padding:1px 6px; border-radius:4px; font-size:0.65rem;'>عاجل</span>"

                sender_label = agent_labels.get(sender, sender)
                receiver_label = agent_labels.get(receiver, receiver)

                st.markdown(
                    f"<div style='background:#1e293b; padding:0.6rem; margin:0.3rem 0; "
                    f"border-radius:8px; border-left: 3px solid {type_color};'>"
                    f"<strong>{sender_label}</strong> → <strong>{receiver_label}</strong> "
                    f"<span style='background:{type_color}; color:#fff; padding:2px 8px; "
                    f"border-radius:4px; font-size:0.75rem;'>{type_label}</span>"
                    f"{priority_badge} "
                    f"<span style='color:#64748b; font-size:0.75rem;'>{timestamp}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            with st.expander("📄 السجل الكامل (JSON)"):
                st.json(log)

        # -- Tab 7: Session History --
        with tab7:
            st.markdown("### 📂 الجلسات السابقة وكشف التناقضات")
            st.markdown("حفظ الجلسات ومقارنة أقوال الأطراف عبر جلسات مختلفة")

            store = SessionStore()

            # Save current session
            st.markdown("#### 💾 حفظ الجلسة الحالية")
            case_number = st.text_input(
                "رقم القضية",
                value="1445/3927",
                key="case_number_input",
            )
            if st.button("💾 حفظ الجلسة في قاعدة البيانات", use_container_width=True):
                session_data = {
                    "full_transcript": results.get("transcription", {}).get("full_transcript", ""),
                    "transcription": results.get("transcription", {}),
                    "legal_analysis": results.get("legal_analysis", {}),
                    "summary": results.get("summary", ""),
                    "qa_review": results.get("qa_review", {}),
                }
                session_id = store.save_session(case_number, session_data)
                st.success(f"تم حفظ الجلسة بنجاح! المعرّف: {session_id}")

            st.markdown("---")

            # Browse previous sessions
            st.markdown("#### 📋 استعراض الجلسات المحفوظة")
            all_cases = store.get_all_cases()

            if all_cases:
                selected_case = st.selectbox("اختر رقم القضية", all_cases)
                sessions = store.get_sessions_for_case(selected_case)

                st.markdown(f"**عدد الجلسات المحفوظة:** {len(sessions)}")
                for i, session in enumerate(sessions):
                    with st.expander(f"📅 جلسة {i+1} — {session['timestamp'][:10]}"):
                        st.markdown(f"**معرّف الجلسة:** `{session['session_id']}`")

                        # Show key facts
                        analysis = session.get("legal_analysis", {})
                        if analysis.get("key_facts"):
                            st.markdown("**الوقائع الجوهرية:**")
                            for fact in analysis["key_facts"]:
                                st.markdown(f"- {fact}")

                        if analysis.get("contradictions"):
                            st.markdown("**تناقضات داخل الجلسة:**")
                            for c in analysis["contradictions"]:
                                st.warning(c)

                # Cross-session contradictions
                st.markdown("---")
                st.markdown("#### 🔍 كشف التناقضات بين الجلسات")
                if st.button("🔍 تحليل التناقضات عبر الجلسات", use_container_width=True):
                    contradictions = store.detect_cross_session_contradictions(selected_case)
                    if contradictions:
                        for c in contradictions:
                            if c["type"] == "cross_session_comparison":
                                st.markdown(
                                    f"<div style='background:#451a03; padding:1rem; margin:0.5rem 0; "
                                    f"border-radius:8px; border-right:3px solid #f59e0b;'>"
                                    f"<strong style='color:#fbbf24;'>⚠️ مقارنة أقوال: {c['speaker']}</strong><br/>"
                                    f"<strong>الجلسة الأولى ({c['session_1_date'][:10]}):</strong><br/>"
                                    + "<br/>".join(f"• {s}" for s in c["session_1_statements"][:3])
                                    + f"<br/><br/><strong>الجلسة الثانية ({c['session_2_date'][:10]}):</strong><br/>"
                                    + "<br/>".join(f"• {s}" for s in c["session_2_statements"][:3])
                                    + f"<br/><br/><em style='color:#94a3b8;'>{c['note']}</em></div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.warning(f"تناقض داخلي في جلسة {c['session_id']}: {c['description']}")
                    else:
                        if len(sessions) < 2:
                            st.info("يجب حفظ جلستين على الأقل لنفس القضية لتفعيل كشف التناقضات بين الجلسات.")
                        else:
                            st.success("لم يتم رصد تناقضات واضحة بين الجلسات.")
            else:
                st.info("لا توجد جلسات محفوظة بعد. قم بتحليل جلسة وحفظها أولاً.")

            # Stats
            st.markdown("---")
            total_sessions = store.get_session_count()
            total_cases = len(all_cases) if all_cases else 0
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.markdown(
                    f"<div class='metric-box'>"
                    f"<div class='number'>{total_sessions}</div>"
                    f"<div class='label'>إجمالي الجلسات المحفوظة</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_s2:
                st.markdown(
                    f"<div class='metric-box'>"
                    f"<div class='number'>{total_cases}</div>"
                    f"<div class='label'>عدد القضايا</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    main()
