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
    initial_sidebar_state="collapsed",
)

# ---- RTL & Custom CSS ----
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap');

    * { font-family: 'Tajawal', sans-serif; }
    html, body, .stApp { direction: rtl; }
    .main .block-container { direction: rtl; text-align: right; max-width: 1200px; }

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

    [data-testid="stSidebar"] { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] .stMarkdown { direction: rtl !important; text-align: right !important; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; flex-direction: row-reverse; }
    .stButton > button { direction: rtl; }
    [data-testid="stChatMessage"] > div { direction: rtl !important; text-align: right !important; }
    .stChatInputContainer { direction: rtl; }
    [data-testid="stChatInput"] textarea { direction: rtl; text-align: right; }
    table { direction: rtl; }
    th, td { text-align: right !important; }
    .stProgress > div { direction: ltr; }
    [data-testid="stFileUploader"] { direction: rtl; }

    /* ===== HERO ===== */
    .hero-container {
        text-align: center;
        padding: 2.5rem 1rem 2rem;
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #22d3ee, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        line-height: 1.3;
    }
    .hero-subtitle {
        font-size: 1.3rem;
        color: #94a3b8;
        font-weight: 400;
        margin-bottom: 0.8rem;
    }
    .hero-slogan {
        font-size: 1.05rem;
        color: #64748b;
        font-style: italic;
        margin-bottom: 1.5rem;
    }
    .hero-badges {
        display: flex;
        justify-content: center;
        gap: 0.8rem;
        flex-wrap: wrap;
        margin-bottom: 1.5rem;
    }
    .hero-badge {
        padding: 0.4rem 1.2rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
    }
    .badge-track { background: linear-gradient(135deg, #059669, #10b981); color: #fff; }
    .badge-cloud { background: linear-gradient(135deg, #7c3aed, #a855f7); color: #fff; }
    .badge-ai { background: linear-gradient(135deg, #0891b2, #22d3ee); color: #fff; }

    /* ===== STATS ROW ===== */
    .stats-row {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin: 1.5rem 0 2rem;
        flex-wrap: wrap;
    }
    .stat-card {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 1.2rem 2rem;
        text-align: center;
        min-width: 140px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .stat-card:hover { border-color: #22d3ee; transform: translateY(-3px); }
    .stat-card .stat-number { font-size: 2.2rem; font-weight: 800; color: #22d3ee; }
    .stat-card .stat-label { font-size: 0.8rem; color: #94a3b8; margin-top: 0.2rem; }

    /* ===== AGENT CARDS ===== */
    .agents-showcase {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 0.8rem;
        margin: 1.5rem 0;
    }
    .agent-showcase-card {
        background: linear-gradient(180deg, #0f172a 0%, #1a2332 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 1.2rem 0.6rem;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .agent-showcase-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #22d3ee, #3b82f6);
        opacity: 0;
        transition: opacity 0.3s;
    }
    .agent-showcase-card:hover::before { opacity: 1; }
    .agent-showcase-card:hover { border-color: #22d3ee; transform: translateY(-4px); box-shadow: 0 8px 25px rgba(34,211,238,0.15); }
    .agent-showcase-card .agent-icon { font-size: 2.2rem; margin-bottom: 0.5rem; }
    .agent-showcase-card .agent-name { font-size: 0.85rem; font-weight: 700; color: #f1f5f9; }
    .agent-showcase-card .agent-desc { font-size: 0.72rem; color: #64748b; margin-top: 0.3rem; line-height: 1.5; }
    .agent-showcase-card .agent-tech-badge {
        display: inline-block; margin-top: 0.5rem;
        background: rgba(34,211,238,0.1); border: 1px solid rgba(34,211,238,0.3);
        border-radius: 6px; padding: 0.15rem 0.5rem; font-size: 0.6rem; color: #22d3ee;
    }

    /* ===== QUALITY LOOP HIGHLIGHT ===== */
    .quality-highlight {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 2px solid #334155;
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin: 1.5rem 0;
        position: relative;
        overflow: hidden;
    }
    .quality-highlight::before {
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 200px; height: 200px;
        background: radial-gradient(circle, rgba(34,211,238,0.05), transparent);
        border-radius: 50%;
    }
    .quality-highlight .qh-title {
        font-size: 1.1rem; font-weight: 700; color: #f1f5f9;
        margin-bottom: 1rem; text-align: center;
    }
    .quality-highlight .qh-flow {
        display: flex; align-items: center; justify-content: center;
        gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0;
    }
    .qh-step {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 0.6rem 1rem;
        text-align: center;
        font-size: 0.8rem;
    }
    .qh-step.reject { border-color: #ef4444; }
    .qh-step.accept { border-color: #22c55e; }
    .qh-arrow { color: #22d3ee; font-size: 1.3rem; font-weight: 700; }
    .qh-arrow-back { color: #f97316; font-size: 1rem; }

    /* ===== CTA SECTION ===== */
    .cta-section {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin: 2rem 0;
    }
    .cta-card {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 2px solid #334155;
        border-radius: 16px;
        padding: 2rem 1.5rem;
        text-align: center;
        transition: border-color 0.3s;
    }
    .cta-card:hover { border-color: #22d3ee; }
    .cta-card .cta-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
    .cta-card .cta-title { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; }
    .cta-card .cta-desc { font-size: 0.85rem; color: #64748b; margin-top: 0.3rem; }

    /* ===== METRIC BOX ===== */
    .metric-box {
        background: #1e293b;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid #334155;
    }
    .metric-box .number { font-size: 2rem; font-weight: 700; color: #22d3ee; }
    .metric-box .label { color: #94a3b8; font-size: 0.85rem; }

    /* ===== CHAT ===== */
    .chat-user {
        background: #1e3a5f; border-radius: 12px; padding: 0.8rem 1rem;
        margin: 0.5rem 0; margin-left: 20%;
    }
    .chat-bot {
        background: #1e293b; border-radius: 12px; padding: 0.8rem 1rem;
        margin: 0.5rem 0; margin-right: 20%; border: 1px solid #334155;
    }

    /* ===== DEMO BADGE ===== */
    .demo-badge {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white; padding: 0.3rem 1rem; border-radius: 20px;
        font-size: 0.8rem; font-weight: 700; display: inline-block; margin-bottom: 1rem;
    }

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; padding: 0.5rem 1rem; }

    /* ===== FLOW ===== */
    .agent-flow-card {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid #334155; border-radius: 12px;
        padding: 0.8rem; text-align: center; transition: all 0.3s ease;
    }
    .agent-flow-card:hover { border-color: #22d3ee; transform: translateY(-2px); }
    .agent-flow-card .icon { font-size: 1.8rem; }
    .agent-flow-card .name { color: #22d3ee; font-size: 0.8rem; font-weight: 700; margin-top: 0.3rem; }
    .agent-flow-card .tech { color: #64748b; font-size: 0.65rem; }
    .flow-arrow { color: #22d3ee; font-size: 1.5rem; display: flex; align-items: center; justify-content: center; height: 100%; }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {
        .agents-showcase { grid-template-columns: repeat(2, 1fr); }
        .cta-section { grid-template-columns: 1fr; }
        .hero-title { font-size: 2.5rem; }
        .stats-row { gap: 1rem; }
    }
</style>
""", unsafe_allow_html=True)


def main():
    # ---- Sidebar ----
    with st.sidebar:
        st.markdown("# ⚖️ مُنصِت")
        st.markdown("**منظومة وكلاء ذكية لتوثيق الجلسات القضائية**")
        st.divider()

        st.markdown("### تخصيص المتحدثين")
        speaker_map = {}
        default_labels = ["القاضي", "المدعي", "المدعى عليه", "محامي المدعي", "محامي المدعى عليه"]
        for i, default in enumerate(default_labels):
            label = st.text_input(f"المتحدث {i+1}", value=default, key=f"spk_{i}")
            speaker_map[f"SPEAKER_{i:02d}"] = label

    # ===============================
    # LANDING PAGE (before results)
    # ===============================
    if "results" not in st.session_state:

        # --- Hero Section ---
        st.markdown("""
        <div class="hero-container">
            <div class="hero-title">⚖️ مُنصِت</div>
            <div class="hero-subtitle">منظومة وكلاء ذكية لتوثيق وتحليل الجلسات القضائية</div>
            <div class="hero-slogan">"كل كلمة في الجلسة... موثّقة، محلّلة، جاهزة للحكم."</div>
            <div class="hero-badges">
                <span class="hero-badge badge-track">Track 04: Agent-to-Agent</span>
                <span class="hero-badge badge-cloud">100% Cloud — بدون GPU</span>
                <span class="hero-badge badge-ai">5 وكلاء ذكيين</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- Stats ---
        st.markdown("""
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-number">5</div>
                <div class="stat-label">وكلاء متخصصين</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">7</div>
                <div class="stat-label">معايير جودة مُوزّنة</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">85%</div>
                <div class="stat-label">حد القبول التلقائي</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">A2A</div>
                <div class="stat-label">تواصل ثنائي الاتجاه</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- Agents Showcase ---
        st.markdown("""
        <div class="agents-showcase">
            <div class="agent-showcase-card">
                <div class="agent-icon">🎙️</div>
                <div class="agent-name">التفريغ الصوتي</div>
                <div class="agent-desc">تفريغ الصوت وتحديد المتحدثين</div>
                <div class="agent-tech-badge">Groq Whisper + pyannote.ai</div>
            </div>
            <div class="agent-showcase-card">
                <div class="agent-icon">⚖️</div>
                <div class="agent-name">التحليل القانوني</div>
                <div class="agent-desc">استخراج الادعاءات والدفوع والأدلة</div>
                <div class="agent-tech-badge">Claude API</div>
            </div>
            <div class="agent-showcase-card">
                <div class="agent-icon">📝</div>
                <div class="agent-name">إنشاء المحضر</div>
                <div class="agent-desc">محضر رسمي + ملخص تنفيذي</div>
                <div class="agent-tech-badge">Claude API</div>
            </div>
            <div class="agent-showcase-card">
                <div class="agent-icon">✅</div>
                <div class="agent-name">مراجعة الجودة</div>
                <div class="agent-desc">تقييم مُهيكل + قرار ذاتي</div>
                <div class="agent-tech-badge">7 معايير مُوزّنة</div>
            </div>
            <div class="agent-showcase-card">
                <div class="agent-icon">💬</div>
                <div class="agent-name">المساعد التفاعلي</div>
                <div class="agent-desc">سؤال وجواب على المحضر</div>
                <div class="agent-tech-badge">Claude API</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- Quality Loop Highlight ---
        st.markdown("""
        <div class="quality-highlight">
            <div class="qh-title">حلقة تحسين الجودة — قرار ذاتي بدون تدخل بشري</div>
            <div class="qh-flow">
                <div class="qh-step">📝 إنشاء المحضر</div>
                <span class="qh-arrow">→</span>
                <div class="qh-step">✅ تقييم (7 معايير)</div>
                <span class="qh-arrow">→</span>
                <div class="qh-step reject">❌ 72% — مرفوض</div>
                <span class="qh-arrow-back">← ملاحظات مُوجّهة</span>
                <span class="qh-arrow">→</span>
                <div class="qh-step">🔄 إعادة إنتاج</div>
                <span class="qh-arrow">→</span>
                <div class="qh-step accept">✅ 96% — مقبول</div>
            </div>
            <p style="text-align:center; color:#64748b; font-size:0.8rem; margin-top:0.8rem;">
                الوكلاء يُحسّنون شغل بعض تلقائياً — وكيل المراجعة يقيّم ويرفض ويُوجّه ملاحظات لكل وكيل حسب نوع المشكلة
            </p>
        </div>
        """, unsafe_allow_html=True)

        # --- CTA Buttons ---
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            demo_clicked = st.button(
                "🎬 تشغيل العرض التجريبي",
                type="primary",
                use_container_width=True,
                help="عرض تجريبي بجلسة محضّرة مسبقاً — لا يحتاج مفاتيح API",
            )

        with col2:
            upload_mode = st.button(
                "📁 رفع تسجيل صوتي",
                use_container_width=True,
                help="رفع تسجيل حقيقي لجلسة قضائية",
            )

        if upload_mode:
            st.session_state["show_upload"] = True

        # --- Demo Mode ---
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
            st.rerun()

        # --- Upload Section ---
        if st.session_state.get("show_upload"):
            st.markdown("---")
            uploaded = st.file_uploader(
                "📁 ارفع التسجيل الصوتي للجلسة",
                type=["mp3", "wav", "m4a", "ogg", "flac", "mp4"],
                help="يدعم: MP3, WAV, M4A, OGG, FLAC, MP4",
            )

            if uploaded is not None:
                st.audio(uploaded)

                if st.button("🚀 ابدأ التحليل", type="primary", use_container_width=True):
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
                    os.unlink(tmp.name)
                    st.rerun()

    # ===============================
    # RESULTS PAGE
    # ===============================
    else:
        results = st.session_state["results"]

        # Top bar
        top_col1, top_col2, top_col3 = st.columns([6, 2, 2])
        with top_col1:
            st.markdown("## ⚖️ مُنصِت — نتائج التحليل")
        with top_col2:
            if results.get("demo_mode"):
                st.markdown('<span class="demo-badge">عرض تجريبي</span>', unsafe_allow_html=True)
        with top_col3:
            if st.button("🔄 تحليل جديد", use_container_width=True):
                del st.session_state["results"]
                if "pipeline" in st.session_state:
                    del st.session_state["pipeline"]
                if "chat_messages" in st.session_state:
                    del st.session_state["chat_messages"]
                st.rerun()

        # --- Quality Loop Summary (always visible at top) ---
        qa_rounds = results.get("qa_rounds", 1)
        qa_round_1 = results.get("qa_round_1", {})
        qa_final = results.get("qa_review", {})

        if qa_rounds >= 2 and qa_round_1:
            score_r1 = qa_round_1.get("completeness_score", 0)
            score_r2 = qa_final.get("completeness_score", 0)
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#0f172a,#1e293b); border:1px solid #334155; "
                f"border-radius:12px; padding:1rem 1.5rem; margin:0.5rem 0 1.5rem;'>"
                f"<div style='display:flex; align-items:center; justify-content:center; gap:1.5rem; flex-wrap:wrap;'>"
                f"<span style='color:#94a3b8; font-size:0.9rem;'>حلقة الجودة:</span>"
                f"<span style='color:#ef4444; font-size:1.3rem; font-weight:700;'>❌ {score_r1}%</span>"
                f"<span style='color:#22d3ee; font-size:1.2rem;'>→ ملاحظات + إعادة إنتاج →</span>"
                f"<span style='color:#22c55e; font-size:1.3rem; font-weight:700;'>✅ {score_r2}%</span>"
                f"<span style='background:#334155; padding:0.3rem 0.8rem; border-radius:6px; color:#f59e0b; font-size:0.8rem;'>"
                f"+{score_r2 - score_r1} نقطة تحسّن</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # --- Agent flow ---
        flow_cols = st.columns([2, 1, 2, 1, 2, 1, 2, 1, 2])
        agents_flow = [
            ("🎙️", "التفريغ", "Whisper + pyannote"),
            None,
            ("⚖️", "التحليل", "Claude API"),
            None,
            ("📝", "المحضر", "Claude API"),
            None,
            ("✅", "المراجعة", "7 معايير"),
            None,
            ("💬", "المساعد", "Claude API"),
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
                    st.markdown("<div class='flow-arrow'>→</div>", unsafe_allow_html=True)

        st.markdown(
            "<div style='text-align:center; padding:0.2rem; color:#f97316; font-size:0.75rem;'>"
            "← ← ملاحظات مُستهدفة (وكيل المراجعة → التلخيص / التحليل) ← ←"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # --- Tabs ---
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🎙️ التفريغ",
            "⚖️ التحليل القانوني",
            "📝 المحضر",
            "✅ الجودة",
            "💬 المساعد",
            "🔗 سجل A2A",
            "📂 الجلسات",
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
                        "محامي المدعي": "#8b5cf6",
                        "محامي المدعى عليه": "#ec4899",
                    }.get(seg["speaker"], "#94a3b8")

                    st.markdown(
                        f"<div style='padding:0.6rem 0.8rem; margin:0.4rem 0; "
                        f"border-right: 4px solid {speaker_color}; "
                        f"background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 8px;'>"
                        f"<strong style='color:{speaker_color}'>{seg['speaker']}</strong> "
                        f"<span style='color:#475569; font-size:0.75rem'>"
                        f"[{seg['start']:.1f}s - {seg['end']:.1f}s]</span><br/>"
                        f"<span style='color:#e2e8f0;'>{seg['text']}</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.text(transcript_data.get("full_transcript", ""))

        # -- Tab 2: Legal Analysis --
        with tab2:
            st.markdown("### التحليل القانوني المُهيكل")
            analysis = results.get("legal_analysis", {})

            if not analysis.get("parse_error"):
                # Agent decisions box
                agent_dec = analysis.get("agent_decisions", {})
                if agent_dec:
                    dec_summary = agent_dec.get("decision_summary", "")
                    flagged = agent_dec.get("articles_flagged", 0)
                    clarifs = agent_dec.get("clarifications_requested", 0)
                    st.markdown(
                        f"<div style='background:linear-gradient(135deg,#0f172a,#1e293b); border:1px solid #334155; "
                        f"border-radius:10px; padding:0.8rem 1.2rem; margin-bottom:1rem;'>"
                        f"<span style='color:#22d3ee; font-weight:700;'>🤖 قرارات الوكيل المستقلة:</span> "
                        f"<span style='color:#e2e8f0;'>{dec_summary}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

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
                    st.markdown("**📖 المواد النظامية (مع تقييم الانطباق):**")
                    for a in analysis.get("legal_articles", []):
                        if isinstance(a, dict):
                            conf = a.get("confidence", 1.0)
                            applicability = a.get("applicability", "applicable")
                            icon = "✅" if applicability == "applicable" else "⚠️" if applicability == "uncertain" else "❌"
                            color = "#22c55e" if applicability == "applicable" else "#f59e0b" if applicability == "uncertain" else "#ef4444"
                            st.markdown(
                                f"<div style='background:#0f172a; padding:0.5rem 0.8rem; margin:0.3rem 0; "
                                f"border-radius:6px; border-right:3px solid {color};'>"
                                f"{icon} {a['article']}<br/>"
                                f"<span style='color:{color}; font-size:0.75rem;'>الثقة: {conf:.0%} — {a.get('reasoning', '')}</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        else:
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

                # Clarification needed
                clarifications = analysis.get("clarification_needed", [])
                if clarifications:
                    st.markdown("---")
                    st.markdown("**🔄 طلبات توضيح أرسلها الوكيل:**")
                    for q in clarifications:
                        st.markdown(
                            f"<div style='background:#1a1033; padding:0.5rem 0.8rem; margin:0.3rem 0; "
                            f"border-radius:6px; border-right:3px solid #a855f7;'>"
                            f"❓ {q}</div>",
                            unsafe_allow_html=True,
                        )

                # Timeline
                timeline = analysis.get("timeline", [])
                if timeline:
                    st.markdown("---")
                    st.markdown("**📅 التسلسل الزمني:**")
                    for t in timeline:
                        st.markdown(f"- {t}")
            else:
                st.json(analysis)

        # -- Tab 3: Summary --
        with tab3:
            st.markdown("### محضر الجلسة والملخص التنفيذي")

            # --- Agent Decision: Detail Level ---
            detail_decision = results.get("detail_decision")
            if detail_decision:
                level = detail_decision.get("level", "standard")
                label = detail_decision.get("label", "قياسي")
                reasoning = detail_decision.get("reasoning", {})

                level_colors = {"brief": "#f59e0b", "standard": "#3b82f6", "detailed": "#8b5cf6"}
                level_icons = {"brief": "📋", "standard": "📄", "detailed": "📑"}
                color = level_colors.get(level, "#3b82f6")
                icon = level_icons.get(level, "📄")

                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #0f172a, #1e293b); border: 1px solid {color};
                            border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.3rem;">{icon}</span>
                        <span style="font-size: 0.9rem; font-weight: 700; color: {color};">🤖 قرار مستقل — مستوى التفصيل: {label}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94a3b8; line-height: 1.8;">
                        وكيل التلخيص قرّر بشكل مستقل أن هذه الجلسة تحتاج محضراً <b style="color:{color};">{label}</b> بناءً على:
                        <br>• عدد الكلمات: <b>{reasoning.get('word_count', '—')}</b>
                        | الادعاءات: <b>{reasoning.get('num_claims', '—')}</b>
                        | الدفوع: <b>{reasoning.get('num_defenses', '—')}</b>
                        | التناقضات: <b>{reasoning.get('num_contradictions', '—')}</b>
                        <br>• درجة التعقيد: <b style="color:{color};">{reasoning.get('complexity_score', '—')}</b> / 6
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(results.get("summary", ""))

        # -- Tab 4: QA Review --
        with tab4:
            # --- Helper: render rubric breakdown table ---
            def render_rubric_table(qa_data, round_label=""):
                rubric = qa_data.get("rubric", [])
                breakdown = qa_data.get("score_breakdown", {})
                criteria_scores = qa_data.get("criteria_scores", {})
                if not rubric or not breakdown:
                    return

                st.markdown(f"**📊 تفصيل الدرجات {round_label}:**")
                header = (
                    "<table style='width:100%; border-collapse:collapse; margin:0.5rem 0;'>"
                    "<tr style='background:#0f172a;'>"
                    "<th style='padding:8px; border:1px solid #334155; color:#94a3b8;'>المعيار</th>"
                    "<th style='padding:8px; border:1px solid #334155; color:#94a3b8; width:55px;'>الوزن</th>"
                    "<th style='padding:8px; border:1px solid #334155; color:#94a3b8; width:65px;'>الدرجة</th>"
                    "<th style='padding:8px; border:1px solid #334155; color:#94a3b8; width:80px;'>المرجّح</th>"
                    "<th style='padding:8px; border:1px solid #334155; color:#94a3b8;'>ملاحظة</th>"
                    "</tr>"
                )
                rows = ""
                for c in rubric:
                    cid = c["id"]
                    bd = breakdown.get(cid, {})
                    cs = criteria_scores.get(cid, {})
                    raw = bd.get("raw_score", 0)
                    weight = bd.get("weight", c.get("weight", 0))
                    weighted = bd.get("weighted_score", 0)
                    notes = cs.get("notes", "") if isinstance(cs, dict) else ""
                    bar_color = "#22c55e" if raw >= 85 else "#f59e0b" if raw >= 60 else "#ef4444"
                    rows += (
                        f"<tr style='background:#1e293b;'>"
                        f"<td style='padding:6px 8px; border:1px solid #334155;'>{c['name']}</td>"
                        f"<td style='padding:6px 8px; border:1px solid #334155; text-align:center !important;'>{weight}%</td>"
                        f"<td style='padding:6px 8px; border:1px solid #334155; text-align:center !important;'>"
                        f"<span style='color:{bar_color}; font-weight:700;'>{raw}</span></td>"
                        f"<td style='padding:6px 8px; border:1px solid #334155; text-align:center !important;'>{weighted}</td>"
                        f"<td style='padding:6px 8px; border:1px solid #334155; color:#94a3b8; font-size:0.8rem;'>{notes}</td>"
                        f"</tr>"
                    )
                st.markdown(header + rows + "</table>", unsafe_allow_html=True)

            # --- Helper: render issues list ---
            def render_issues(issues, border_color="#ef4444"):
                criterion_labels = {
                    "parties": "الأطراف", "claims": "الادعاءات", "evidence": "الأدلة",
                    "articles": "المواد النظامية", "contradictions": "التناقضات",
                    "decisions": "القرارات", "financials": "المبالغ والتواريخ",
                }
                type_labels = {
                    "missing_info": "معلومات مفقودة", "inaccuracy": "خطأ",
                    "contradiction": "تناقض", "suggestion": "اقتراح",
                }
                for issue in issues:
                    severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue.get("severity", ""), "⚪")
                    type_label = type_labels.get(issue.get("type", ""), issue.get("type", ""))
                    crit = criterion_labels.get(issue.get("criterion", ""), "")
                    crit_badge = f" <span style='background:#334155; padding:1px 6px; border-radius:4px; font-size:0.7rem;'>{crit}</span>" if crit else ""
                    st.markdown(
                        f"<div style='background:#1e293b; padding:0.5rem 0.8rem; margin:0.3rem 0; "
                        f"border-radius:6px; border-right:3px solid {border_color};'>"
                        f"{severity_icon} <strong>{type_label}</strong>{crit_badge}: {issue.get('description', '')}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            if qa_rounds >= 2 and qa_round_1:
                st.markdown("### حلقة تحسين الجودة — تقييم مُهيكل بمعايير مُوزّنة")

                score_r1 = qa_round_1.get("completeness_score", 0)
                score_r2 = qa_final.get("completeness_score", 0)
                improvement = score_r2 - score_r1
                threshold = qa_round_1.get("quality_threshold", 85)

                st.markdown(
                    f"<div style='background:linear-gradient(135deg,#0f172a,#1e293b); border:1px solid #334155; "
                    f"border-radius:12px; padding:1.2rem; margin:1rem 0;'>"
                    f"<div style='display:flex; justify-content:space-around; text-align:center; flex-wrap:wrap;'>"
                    f"<div>"
                    f"<div style='font-size:2.5rem; font-weight:700; color:#ef4444;'>{score_r1}%</div>"
                    f"<div style='color:#94a3b8; font-size:0.85rem;'>الجولة الأولى</div>"
                    f"<div style='color:#ef4444; font-size:0.8rem;'>❌ مرفوض</div>"
                    f"</div>"
                    f"<div style='display:flex; align-items:center;'>"
                    f"<div style='font-size:1.8rem; color:#22d3ee;'>→ +{improvement} →</div>"
                    f"</div>"
                    f"<div>"
                    f"<div style='font-size:2.5rem; font-weight:700; color:#22c55e;'>{score_r2}%</div>"
                    f"<div style='color:#94a3b8; font-size:0.85rem;'>الجولة الثانية</div>"
                    f"<div style='color:#22c55e; font-size:0.8rem;'>✅ مقبول</div>"
                    f"</div>"
                    f"<div style='display:flex; align-items:center;'>"
                    f"<div style='background:#334155; padding:0.5rem 1rem; border-radius:8px;'>"
                    f"<div style='color:#94a3b8; font-size:0.7rem;'>حد القبول</div>"
                    f"<div style='color:#f59e0b; font-size:1.5rem; font-weight:700;'>{threshold}%</div>"
                    f"</div></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

                # Round 1
                st.markdown("---")
                st.markdown("#### ❌ الجولة الأولى — مرفوض")
                render_rubric_table(qa_round_1, "(الجولة الأولى)")

                r1_issues = qa_round_1.get("issues", [])
                if r1_issues:
                    st.markdown("**الملاحظات التي أدت للرفض:**")
                    render_issues(r1_issues, "#ef4444")

                feedback_sent = qa_round_1.get("feedback_sent", [])
                if feedback_sent:
                    st.markdown("**📨 توجيه الملاحظات:**")
                    agent_labels_qa = {"summary_agent": "وكيل التلخيص 📝", "legal_analysis_agent": "وكيل التحليل ⚖️"}
                    for fb in feedback_sent:
                        target = agent_labels_qa.get(fb.get("to", ""), fb.get("to", ""))
                        issues_list = fb.get("issues", [])
                        issues_text = "، ".join(issues_list) if isinstance(issues_list, list) and issues_list and isinstance(issues_list[0], str) else ""
                        st.markdown(
                            f"<div style='background:#451a03; padding:0.5rem 0.8rem; margin:0.3rem 0; "
                            f"border-radius:6px; border-right:3px solid #f97316;'>"
                            f"✅ المراجعة → <strong>{target}</strong>"
                            f"{': ' + issues_text if issues_text else ''}</div>",
                            unsafe_allow_html=True,
                        )

                # Round 2
                st.markdown("---")
                st.markdown("#### ✅ الجولة الثانية — مقبول")
                render_rubric_table(qa_final, "(الجولة الثانية)")

                improvement_data = qa_final.get("improvement_from_round1", {})
                criteria_imp = improvement_data.get("criteria_improvements", {})
                if criteria_imp:
                    criterion_labels = {
                        "parties": "الأطراف", "claims": "الادعاءات", "evidence": "الأدلة",
                        "articles": "المواد النظامية", "contradictions": "التناقضات",
                        "decisions": "القرارات", "financials": "المبالغ",
                    }
                    st.markdown("**📈 التحسين لكل معيار:**")
                    imp_html = ""
                    for cid, data in criteria_imp.items():
                        label = criterion_labels.get(cid, cid)
                        imp_html += (
                            f"<div style='display:inline-block; background:#0f172a; border:1px solid #334155; "
                            f"border-radius:8px; padding:0.4rem 0.7rem; margin:0.2rem; text-align:center;'>"
                            f"<div style='color:#94a3b8; font-size:0.7rem;'>{label}</div>"
                            f"<span style='color:#ef4444;'>{data['before']}</span>"
                            f" → <span style='color:#22c55e;'>{data['after']}</span>"
                            f"</div>"
                        )
                    st.markdown(f"<div style='display:flex; flex-wrap:wrap; gap:0.2rem;'>{imp_html}</div>", unsafe_allow_html=True)

                st.success(qa_final.get("overall_assessment", ""))

                if improvement_data.get("issues_resolved"):
                    with st.expander("المشكلات التي تم حلها"):
                        for r in improvement_data["issues_resolved"]:
                            st.markdown(f"- ✅ {r}")

            else:
                st.markdown("### تقرير مراجعة الجودة")
                qa = qa_final
                if not qa.get("parse_error"):
                    score = qa.get("completeness_score", 0)
                    decision = qa.get("decision", "")
                    decision_icon = "✅ مقبول" if decision == "accept" else "❌ مرفوض"
                    decision_color = "#22c55e" if decision == "accept" else "#ef4444"
                    st.markdown(
                        f"<div class='metric-box'>"
                        f"<div class='number'>{score}%</div>"
                        f"<div class='label'>الدرجة المرجّحة</div>"
                        f"<div style='color:{decision_color}; font-size:1.1rem; font-weight:700; margin-top:0.5rem;'>{decision_icon}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.progress(score / 100)
                    render_rubric_table(qa)
                    st.info(qa.get("overall_assessment", ""))
                else:
                    st.json(qa)

        # -- Tab 5: Chatbot --
        with tab5:
            st.markdown("### 💬 اسأل عن الجلسة")

            if "chat_messages" not in st.session_state:
                st.session_state["chat_messages"] = []

            for msg in st.session_state["chat_messages"]:
                css_class = "chat-user" if msg["role"] == "user" else "chat-bot"
                prefix = "👤" if msg["role"] == "user" else "🤖"
                st.markdown(
                    f"<div class='{css_class}'>{prefix} {msg['content']}</div>",
                    unsafe_allow_html=True,
                )

            quick_qs = ["ما هي طلبات المدعي؟", "ما موقف المدعى عليه؟", "ما المواد النظامية؟", "لخّص الجلسة"]
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
            st.markdown("### 🔗 سجل تواصل الوكلاء (A2A)")

            stats = results.get("a2a_stats", {})
            agent_labels = {
                "pipeline": "المنسّق", "transcription_agent": "التفريغ",
                "legal_analysis_agent": "التحليل", "summary_agent": "التلخيص",
                "qa_agent": "المراجعة", "chatbot_agent": "المساعد", "user": "المستخدم",
            }
            if stats:
                stat_cols = st.columns(min(len(stats), 6))
                for i, (agent, data) in enumerate(stats.items()):
                    if i < len(stat_cols):
                        with stat_cols[i]:
                            label = agent_labels.get(agent, agent)
                            st.markdown(
                                f"<div class='metric-box'>"
                                f"<div class='number' style='font-size:1.2rem'>{data['sent'] + data['received']}</div>"
                                f"<div class='label'>{label}</div>"
                                f"<div style='font-size:0.65rem; color:#64748b;'>"
                                f"↑{data['sent']} ↓{data['received']}"
                                f"{' 💬' + str(data['feedbacks']) if data.get('feedbacks') else ''}"
                                f"</div></div>",
                                unsafe_allow_html=True,
                            )
                st.markdown("---")

            log = results.get("a2a_log", [])
            for entry in log:
                sender = entry.get("sender", "")
                receiver = entry.get("receiver", "")
                msg_type = entry.get("msg_type", "")
                timestamp = entry.get("timestamp", "")
                priority = entry.get("priority", "normal")

                type_color = {
                    "data": "#3b82f6", "response": "#22c55e", "request": "#f59e0b",
                    "clarification_request": "#a855f7", "clarification_response": "#8b5cf6",
                    "feedback": "#f97316",
                }.get(msg_type, "#94a3b8")

                type_label = {
                    "data": "بيانات", "response": "استجابة", "request": "طلب",
                    "clarification_request": "طلب توضيح", "clarification_response": "رد توضيح",
                    "feedback": "ملاحظة جودة",
                }.get(msg_type, msg_type)

                priority_badge = ""
                if priority == "high":
                    priority_badge = " <span style='background:#ef4444; color:#fff; padding:1px 5px; border-radius:4px; font-size:0.6rem;'>عاجل</span>"

                st.markdown(
                    f"<div style='background:#1e293b; padding:0.5rem 0.8rem; margin:0.2rem 0; "
                    f"border-radius:6px; border-left:3px solid {type_color};'>"
                    f"<strong>{agent_labels.get(sender, sender)}</strong> → "
                    f"<strong>{agent_labels.get(receiver, receiver)}</strong> "
                    f"<span style='background:{type_color}; color:#fff; padding:1px 6px; "
                    f"border-radius:4px; font-size:0.7rem;'>{type_label}</span>"
                    f"{priority_badge}</div>",
                    unsafe_allow_html=True,
                )

            with st.expander("📄 السجل الكامل (JSON)"):
                st.json(log)

        # -- Tab 7: Session History --
        with tab7:
            st.markdown("### 📂 الجلسات السابقة")

            store = SessionStore()

            case_number = st.text_input("رقم القضية", value="1445/3927", key="case_number_input")
            if st.button("💾 حفظ الجلسة", use_container_width=True):
                session_data = {
                    "full_transcript": results.get("transcription", {}).get("full_transcript", ""),
                    "transcription": results.get("transcription", {}),
                    "legal_analysis": results.get("legal_analysis", {}),
                    "summary": results.get("summary", ""),
                    "qa_review": results.get("qa_review", {}),
                }
                session_id = store.save_session(case_number, session_data)
                st.success(f"تم الحفظ! المعرّف: {session_id}")

            st.markdown("---")
            all_cases = store.get_all_cases()

            if all_cases:
                selected_case = st.selectbox("اختر القضية", all_cases)
                sessions = store.get_sessions_for_case(selected_case)
                st.markdown(f"**{len(sessions)} جلسة محفوظة**")

                for i, session in enumerate(sessions):
                    with st.expander(f"جلسة {i+1} — {session['timestamp'][:10]}"):
                        analysis = session.get("legal_analysis", {})
                        if analysis.get("key_facts"):
                            for fact in analysis["key_facts"]:
                                st.markdown(f"- {fact}")

                st.markdown("---")
                if st.button("🔍 كشف التناقضات بين الجلسات", use_container_width=True):
                    contradictions = store.detect_cross_session_contradictions(selected_case)
                    if contradictions:
                        for c in contradictions:
                            if c["type"] == "cross_session_comparison":
                                st.warning(f"⚠️ تناقض محتمل في أقوال {c['speaker']}")
                            else:
                                st.warning(c.get("description", ""))
                    elif len(sessions) < 2:
                        st.info("يجب حفظ جلستين على الأقل لكشف التناقضات.")
                    else:
                        st.success("لا تناقضات.")
            else:
                st.info("لا توجد جلسات محفوظة بعد.")


if __name__ == "__main__":
    main()
