# app.py — CV Analyzer · Modern ATS-aware UI
# Çalıştırmak için: streamlit run app.py

import io
import logging
import warnings
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.WARNING)

import streamlit as st

from cv_utils import (
    extract_pdf_full,
    detect_sections,
    detect_contact_info,
    extract_keywords_from_text,
    extract_keywords_from_job,
    compute_keyword_gap,
    compute_programmatic_ats_score,
    extract_job_posting,
)
from analyzer import analyze_ats, analyze_cv

# ── Sayfa yapılandırması ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="CV Analyzer · ATS Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS Tasarım Sistemi ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg:          #0A0C12;
    --bg-card:     #10131C;
    --bg-hover:    #161A27;
    --border:      #1E2235;
    --border-glow: #2A3050;
    --text-primary:   #E8EAF0;
    --text-secondary: #7A8BA8;
    --text-muted:     #4A5570;
    --accent:    #4F8DFF;
    --accent2:   #7C5CFC;
    --success:   #22C55E;
    --warning:   #F59E0B;
    --danger:    #EF4444;
    --teal:      #00D4AA;
    --radius:    12px;
    --radius-lg: 20px;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text-primary) !important;
}

[data-testid="stAppViewContainer"] > .main {
    background: var(--bg) !important;
}

[data-testid="block-container"] {
    padding: 2rem 3rem !important;
    max-width: 1200px;
    margin: 0 auto;
}

/* Sidebar gizle */
[data-testid="stSidebar"] { display: none; }
#MainMenu, footer, header { visibility: hidden; }

/* Global font override — semantik elementler */
p, h1, h2, h3, h4, h5, h6, li, span.text,
div.stMarkdown, div.stMarkdown *,
label, .stTextInput input, .stTextArea textarea {
    font-family: 'Inter', sans-serif !important;
}

/* ── Hero ─────────────────────────────────────────────────────────────────── */
.hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 28px 36px;
    background: linear-gradient(135deg, #10131C 0%, #131828 50%, #0F1420 100%);
    border: 1px solid var(--border-glow);
    border-radius: var(--radius-lg);
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(79,141,255,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Syne', sans-serif !important;
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #E8EAF0 0%, #4F8DFF 60%, #7C5CFC 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    line-height: 1;
    margin-bottom: 6px;
}
.hero-sub {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem;
    color: var(--text-muted);
    letter-spacing: 0.08em;
}
.hero-badge {
    background: rgba(79,141,255,0.1);
    border: 1px solid rgba(79,141,255,0.3);
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    padding: 6px 14px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.hero-badge::before {
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--teal);
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(0.8); }
}

/* ── Tab Selector ─────────────────────────────────────────────────────────── */
.tab-row {
    display: flex;
    gap: 12px;
    margin-bottom: 28px;
}
.tab-btn {
    flex: 1;
    padding: 16px 24px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-card);
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
}
.tab-btn.active {
    border-color: var(--accent);
    background: rgba(79,141,255,0.08);
}
.tab-icon { font-size: 1.5rem; margin-bottom: 6px; }
.tab-title {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--text-primary);
}
.tab-desc {
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-top: 3px;
}

/* ── Upload Zone ─────────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background: var(--bg-card) !important;
    border: 2px dashed var(--border-glow) !important;
    border-radius: var(--radius) !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
}
[data-testid="stFileUploader"] label {
    color: var(--text-secondary) !important;
}

/* ── Card ─────────────────────────────────────────────────────────────────── */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 20px;
}
.card-title {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--text-muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.card-title::before {
    content: '';
    width: 3px; height: 14px;
    background: var(--accent);
    border-radius: 2px;
    display: inline-block;
}

/* ── Score Ring ───────────────────────────────────────────────────────────── */
.score-ring-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px 24px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
}
.score-ring {
    position: relative;
    width: 180px; height: 180px;
}
.score-ring svg {
    transform: rotate(-90deg);
    width: 180px; height: 180px;
}
.score-ring circle.track {
    fill: none;
    stroke: var(--border);
    stroke-width: 14;
}
.score-ring circle.fill {
    fill: none;
    stroke-width: 14;
    stroke-linecap: round;
    transition: stroke-dashoffset 1s ease;
}
.score-ring .center {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
}
.score-number {
    font-family: 'Syne', sans-serif !important;
    font-size: 3rem;
    font-weight: 800;
    line-height: 1;
}
.score-label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.08em;
    margin-top: 4px;
}
.verdict-badge {
    margin-top: 20px;
    padding: 10px 20px;
    border-radius: 8px;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem;
    font-weight: 500;
    text-align: center;
    line-height: 1.4;
}

/* ── Sub-score Bar ─────────────────────────────────────────────────────────── */
.subscore-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
}
.subscore-label {
    font-size: 0.82rem;
    color: var(--text-secondary);
    width: 120px;
    flex-shrink: 0;
}
.subscore-bar-bg {
    flex: 1;
    height: 8px;
    background: var(--border);
    border-radius: 4px;
    overflow: hidden;
}
.subscore-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.8s ease;
}
.subscore-value {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem;
    font-weight: 500;
    width: 36px;
    text-align: right;
    flex-shrink: 0;
}

/* ── Keyword Chip ─────────────────────────────────────────────────────────── */
.chips-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
}
.chip {
    padding: 4px 12px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.02em;
}
.chip-green {
    background: rgba(34,197,94,0.12);
    border: 1px solid rgba(34,197,94,0.3);
    color: #4ADE80;
}
.chip-red {
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.3);
    color: #F87171;
}
.chip-amber {
    background: rgba(245,158,11,0.12);
    border: 1px solid rgba(245,158,11,0.3);
    color: #FCD34D;
}
.chip-blue {
    background: rgba(79,141,255,0.12);
    border: 1px solid rgba(79,141,255,0.3);
    color: #7EB8FF;
}
.chip-teal {
    background: rgba(0,212,170,0.12);
    border: 1px solid rgba(0,212,170,0.3);
    color: #2DD4BF;
}

/* ── Section Checklist ─────────────────────────────────────────────────────── */
.section-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.85rem;
}
.section-item:last-child { border-bottom: none; }
.section-check { font-size: 1rem; width: 20px; }
.section-name { flex: 1; color: var(--text-primary); }
.section-status {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.68rem;
    padding: 3px 8px;
    border-radius: 4px;
}
.status-ok     { background: rgba(34,197,94,0.15);  color: #4ADE80; }
.status-miss   { background: rgba(239,68,68,0.15);  color: #F87171; }
.status-bonus  { background: rgba(79,141,255,0.15); color: #7EB8FF; }

/* ── Recommendation Card ──────────────────────────────────────────────────── */
.rec-card {
    display: flex;
    gap: 14px;
    padding: 14px 16px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    margin-bottom: 10px;
}
.rec-priority {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    padding: 4px 8px;
    border-radius: 4px;
    height: fit-content;
    white-space: nowrap;
    flex-shrink: 0;
}
.priority-high   { background: rgba(239,68,68,0.15);  color: #F87171; }
.priority-medium { background: rgba(245,158,11,0.15); color: #FCD34D; }
.priority-low    { background: rgba(34,197,94,0.15);  color: #4ADE80; }
.rec-body { flex: 1; }
.rec-action {
    font-size: 0.88rem;
    color: var(--text-primary);
    font-weight: 500;
    margin-bottom: 4px;
}
.rec-reason {
    font-size: 0.78rem;
    color: var(--text-secondary);
}

/* ── ATS Compat ───────────────────────────────────────────────────────────── */
.compat-row {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-top: 8px;
}
.compat-item {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.compat-name {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem;
    color: var(--text-secondary);
}
.compat-score {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.1rem;
    font-weight: 700;
}

/* ── Quick Win ────────────────────────────────────────────────────────────── */
.quick-win {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 14px;
    background: rgba(0,212,170,0.05);
    border: 1px solid rgba(0,212,170,0.2);
    border-radius: 8px;
    margin-bottom: 8px;
    font-size: 0.85rem;
    color: var(--text-primary);
}
.quick-win-icon { color: var(--teal); font-size: 1rem; flex-shrink: 0; }

/* ── Streamlit overrides ──────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.05em !important;
    padding: 14px 28px !important;
    transition: opacity 0.2s, transform 0.1s !important;
}
.stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}
.stTextInput input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    padding: 12px 16px !important;
    font-size: 0.88rem !important;
}
.stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(79,141,255,0.15) !important;
}
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: 1px solid var(--border-glow) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "mode":       "ats",   # "ats" | "match"
        "result":     None,
        "prog":       None,
        "analyzed":   False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── Yardımcılar ──────────────────────────────────────────────────────────────

def _score_color(score: int) -> str:
    if score >= 75: return "#22C55E"
    if score >= 55: return "#F59E0B"
    return "#EF4444"

def _score_label(score: int) -> str:
    if score >= 80: return "Mükemmel"
    if score >= 65: return "İyi"
    if score >= 50: return "Orta"
    if score >= 35: return "Zayıf"
    return "Kritik"

def _score_ring(score: int, label: str = "ATS SKORU") -> str:
    color = _score_color(score)
    r = 76
    circ = 2 * 3.14159 * r
    offset = circ * (1 - score / 100)
    return f"""
    <div class="score-ring-wrap">
        <div class="score-ring">
            <svg viewBox="0 0 180 180">
                <circle class="track" cx="90" cy="90" r="{r}"/>
                <circle class="fill" cx="90" cy="90" r="{r}"
                    stroke="{color}"
                    stroke-dasharray="{circ:.1f}"
                    stroke-dashoffset="{offset:.1f}"/>
            </svg>
            <div class="center">
                <div class="score-number" style="color:{color}">{score}</div>
                <div class="score-label">{label}</div>
            </div>
        </div>
    </div>
    """

def _subscore_bar(label: str, score: int, emoji: str = "") -> str:
    color = _score_color(score)
    return f"""
    <div class="subscore-row">
        <div class="subscore-label">{emoji} {label}</div>
        <div class="subscore-bar-bg">
            <div class="subscore-bar-fill" style="width:{score}%;background:{color}"></div>
        </div>
        <div class="subscore-value" style="color:{color}">{score}</div>
    </div>
    """

def _chips(items: list, cls: str) -> str:
    if not items:
        return "<span style='color:#4A5570;font-size:0.8rem'>—</span>"
    return "<div class='chips-wrap'>" + "".join(
        f"<span class='chip {cls}'>{i}</span>" for i in items
    ) + "</div>"

def _section_row(name: str, found: bool, critical: bool = False) -> str:
    if found:
        icon, label, cls = "✓", "Mevcut", "status-ok"
    elif critical:
        icon, label, cls = "✗", "Eksik — Kritik", "status-miss"
    else:
        icon, label, cls = "○", "Opsiyonel", "status-bonus"

    display = {
        "experience": "İş Deneyimi", "education": "Eğitim",
        "skills": "Beceriler", "summary": "Özet / Profil",
        "certifications": "Sertifikalar", "projects": "Projeler",
        "contact": "İletişim", "languages": "Diller",
        "awards": "Ödüller", "volunteer": "Gönüllülük / Staj",
    }.get(name, name.title())

    return f"""
    <div class="section-item">
        <span class="section-check" style="color:{'#4ADE80' if found else '#F87171' if critical else '#4A5570'}">{icon}</span>
        <span class="section-name">{display}</span>
        <span class="section-status {cls}">{label}</span>
    </div>
    """

def _rec_card(rec: dict) -> str:
    p = rec.get("priority", "medium").lower()
    p_label = {"high": "YÜKSEK", "medium": "ORTA", "low": "DÜŞÜK"}.get(p, "ORTA")
    return f"""
    <div class="rec-card">
        <span class="rec-priority priority-{p}">{p_label}</span>
        <div class="rec-body">
            <div class="rec-action">{rec.get('action','')}</div>
            <div class="rec-reason">{rec.get('reason','')}</div>
        </div>
    </div>
    """

def _quick_win(text: str) -> str:
    return f"""<div class="quick-win">
        <span class="quick-win-icon">⚡</span>
        <span>{text}</span>
    </div>"""

def _compat_grid(compat: dict) -> str:
    items = ""
    for name, score in compat.items():
        color = _score_color(score)
        items += f"""
        <div class="compat-item">
            <span class="compat-name">{name.upper()}</span>
            <span class="compat-score" style="color:{color}">{score}</span>
        </div>
        """
    return f'<div class="compat-row">{items}</div>'


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div>
        <div class="hero-title">CV Analyzer</div>
        <div class="hero-sub">// ats intelligence · resume optimization engine</div>
    </div>
    <div class="hero-badge">GROQ · llama-3.3-70b-versatile</div>
</div>
""", unsafe_allow_html=True)


# ── Mod seçimi ────────────────────────────────────────────────────────────────
col_m1, col_m2 = st.columns(2)
with col_m1:
    if st.button("🤖  ATS Skoru Al\nGenel ATS uyumluluğunu analiz et", use_container_width=True):
        st.session_state.mode = "ats"
        st.session_state.result = None
        st.session_state.analyzed = False
with col_m2:
    if st.button("🔗  İş İlanıyla Karşılaştır\nSpesifik pozisyon için keyword gap analizi", use_container_width=True):
        st.session_state.mode = "match"
        st.session_state.result = None
        st.session_state.analyzed = False

# Aktif mod göstergesi
mode_label = "ATS SKORU" if st.session_state.mode == "ats" else "İŞ İLANI KARŞILAŞTIRMA"
st.markdown(f"""
<div style="margin: 12px 0 28px 0;display:flex;align-items:center;gap:10px;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                 color:#4F8DFF;letter-spacing:0.1em;background:rgba(79,141,255,0.1);
                 border:1px solid rgba(79,141,255,0.25);border-radius:6px;
                 padding:5px 12px;">● {mode_label}</span>
</div>
""", unsafe_allow_html=True)


# ── Input Bölümü ──────────────────────────────────────────────────────────────
col_inp, col_gap = st.columns([2, 1])
with col_inp:
    uploaded_cv = st.file_uploader(
        "CV'ni buraya yükle (PDF)",
        type=["pdf"],
        help="ATS sistemlerinin büyük çoğunluğu PDF'i destekler.",
        label_visibility="visible",
    )

    job_url = None
    if st.session_state.mode == "match":
        job_url = st.text_input(
            "İş ilanı URL'si",
            placeholder="https://linkedin.com/jobs/view/...",
            help="LinkedIn, kariyer.net, şirket kariyer sayfası — hepsi desteklenir.",
        )

    analyze_btn = st.button(
        "ANALİZİ BAŞLAT →",
        type="primary",
        use_container_width=True,
    )

with col_gap:
    st.markdown("""
    <div class="card" style="margin-top:0">
        <div class="card-title">ATS Nasıl Çalışır?</div>
        <div style="font-size:0.82rem;color:#7A8BA8;line-height:1.7">
            <div style="margin-bottom:8px">
                <span style="color:#4F8DFF;font-weight:600">%35</span> Keyword gücü
            </div>
            <div style="margin-bottom:8px">
                <span style="color:#22C55E;font-weight:600">%25</span> Bölüm yapısı
            </div>
            <div style="margin-bottom:8px">
                <span style="color:#F59E0B;font-weight:600">%20</span> Format uyumu
            </div>
            <div>
                <span style="color:#7C5CFC;font-weight:600">%20</span> İletişim bilgisi
            </div>
        </div>
        <div style="margin-top:16px;padding-top:14px;border-top:1px solid #1E2235;
                    font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#4A5570">
            80+ → Excellent<br>
            60–79 → Good<br>
            40–59 → Needs Work<br>
            &lt;40 → Danger Zone
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Analiz ───────────────────────────────────────────────────────────────────
if analyze_btn:
    if not uploaded_cv:
        st.warning("Lütfen CV dosyası yükle.")
        st.stop()
    if st.session_state.mode == "match" and not job_url:
        st.warning("Lütfen iş ilanı URL'sini gir.")
        st.stop()

    with st.spinner("Analiz yapılıyor — programmatic tarama + LLM yorumlama..."):

        # 1. PDF parse
        pdf_meta = extract_pdf_full(uploaded_cv)
        cv_text  = pdf_meta["text"]

        if len(cv_text.strip()) < 50:
            st.error("PDF'ten metin çıkarılamadı. CV'nin metin tabanlı (taranmış değil) bir PDF olduğundan emin ol.")
            st.stop()

        # 2. Programmatic tarama
        sections = detect_sections(cv_text)
        contact  = detect_contact_info(cv_text)
        keywords = extract_keywords_from_text(cv_text)
        scores   = compute_programmatic_ats_score(pdf_meta, sections, contact, keywords)

        prog = {
            "pdf_meta": pdf_meta,
            "sections": sections,
            "contact":  contact,
            "keywords": keywords,
            "scores":   scores,
        }

        # 3. LLM analizi
        if st.session_state.mode == "ats":
            result = analyze_ats(cv_text, prog)
            result_type = "ats"
        else:
            job_text = extract_job_posting(job_url)
            if not job_text:
                st.error("İş ilanı çekilemedi. URL'yi kontrol et.")
                st.stop()
            job_kw   = extract_keywords_from_job(job_text)
            kw_gap   = compute_keyword_gap(keywords, job_kw)
            prog["keyword_gap"] = kw_gap
            result = analyze_cv(cv_text, job_text, prog)
            result_type = "match"

        st.session_state.result      = result
        st.session_state.prog        = prog
        st.session_state.result_type = result_type
        st.session_state.analyzed    = True

    st.success("✓ Analiz tamamlandı!")


# ── Sonuç Görüntüleme ────────────────────────────────────────────────────────
if st.session_state.analyzed and st.session_state.result:
    result = st.session_state.result
    prog   = st.session_state.prog
    rtype  = st.session_state.result_type

    scores   = prog["scores"]
    sections = prog["sections"]
    contact  = prog["contact"]
    keywords = prog["keywords"]

    st.markdown("<hr style='border:1px solid #1E2235;margin:32px 0'>", unsafe_allow_html=True)

    # ── ATS Modu Sonuç ──────────────────────────────────────────────────────
    if rtype == "ats":
        ats_score = result.get("ats_score", scores["total"])
        color     = _score_color(ats_score)
        verdict   = result.get("verdict", "")

        col_ring, col_subs = st.columns([1, 2])

        with col_ring:
            # Score ring
            st.markdown(_score_ring(ats_score, "ATS SKORU"), unsafe_allow_html=True)
            st.markdown(f"""
            <div class="verdict-badge" style="background:rgba({
                '34,197,94' if ats_score>=75 else '245,158,11' if ats_score>=55 else '239,68,68'
            },0.1);border:1px solid {color}40;color:{color}">
                {verdict}
            </div>
            """, unsafe_allow_html=True)

        with col_subs:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">ALT SKOR DAĞILIMI</div>', unsafe_allow_html=True)
            st.markdown(
                _subscore_bar("Keyword Gücü",    scores["keyword_score"], "🔑") +
                _subscore_bar("Bölüm Yapısı",    scores["section_score"], "📋") +
                _subscore_bar("Format Uyumu",    scores["format_score"],  "📐") +
                _subscore_bar("İletişim Bilgisi", scores["contact_score"], "📬"),
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # Row 2: Sections + Contact + Keywords
        col_sec, col_kw = st.columns([1, 1])

        with col_sec:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">BÖLÜM KONTROLÜ</div>', unsafe_allow_html=True)
            critical = ["experience", "education", "skills"]
            bonus    = ["summary", "certifications", "projects", "contact", "languages", "awards", "volunteer"]
            html_rows = ""
            for s in critical:
                html_rows += _section_row(s, sections.get(s, False), critical=True)
            for s in bonus:
                html_rows += _section_row(s, sections.get(s, False), critical=False)
            st.markdown(html_rows, unsafe_allow_html=True)

            # Contact chips
            st.markdown('<div style="margin-top:16px;padding-top:14px;border-top:1px solid #1E2235">', unsafe_allow_html=True)
            st.markdown('<div class="card-title" style="margin-bottom:10px">İLETİŞİM BİLGİSİ</div>', unsafe_allow_html=True)
            contact_items = []
            for field in ["email","phone","linkedin","github","website"]:
                val = contact.get(field)
                if val:
                    contact_items.append(f'<span class="chip chip-green">✓ {field}</span>')
                else:
                    contact_items.append(f'<span class="chip chip-red">✗ {field}</span>')
            st.markdown(f'<div class="chips-wrap">{"".join(contact_items)}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_kw:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">BULUNAN TEKNİK BECERİLER</div>', unsafe_allow_html=True)
            st.markdown(_chips(keywords["tech_skills"], "chip-blue"), unsafe_allow_html=True)

            st.markdown('<div class="card-title" style="margin-top:18px">ETKİ FİİLLERİ</div>', unsafe_allow_html=True)
            st.markdown(_chips(keywords["impact_verbs"], "chip-teal"), unsafe_allow_html=True)

            density = keywords["keyword_density"]
            dens_color = "#22C55E" if 1 <= density <= 3 else "#F59E0B" if density < 1 else "#EF4444"
            st.markdown(f"""
            <div style="margin-top:18px;padding:12px 14px;background:var(--bg);
                        border:1px solid var(--border);border-radius:8px;
                        display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:0.8rem;color:var(--text-secondary)">Keyword Yoğunluğu</span>
                <span style="font-family:'JetBrains Mono',monospace;font-weight:600;color:{dens_color}">
                    {density:.1f}% <span style="color:var(--text-muted);font-size:0.7rem">(ideal: 1–3%)</span>
                </span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Row 3: Quick wins + ATS compat
        col_qw, col_compat = st.columns([1, 1])

        with col_qw:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">QUICK WINS ⚡</div>', unsafe_allow_html=True)
            quick_wins = result.get("quick_wins", [])
            if quick_wins:
                for w in quick_wins:
                    st.markdown(_quick_win(w), unsafe_allow_html=True)
            else:
                st.markdown('<span style="color:#4A5570;font-size:0.8rem">Önerilmiyor — skor zaten yüksek</span>', unsafe_allow_html=True)

            # Format issues
            fmt_issues = result.get("format_issues", []) + scores.get("format_penalties", [])
            if fmt_issues:
                st.markdown('<div class="card-title" style="margin-top:18px">FORMAT SORUNLARI</div>', unsafe_allow_html=True)
                for issue in fmt_issues[:4]:
                    st.markdown(f"""
                    <div style="display:flex;gap:8px;padding:8px 0;border-bottom:1px solid #1E2235;
                                font-size:0.82rem;color:#F87171;align-items:flex-start">
                        <span>⚠</span><span>{issue}</span>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_compat:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">ATS UYUMLULUK MATRİSİ</div>', unsafe_allow_html=True)
            compat = result.get("ats_compatibility", {
                "greenhouse": 70, "taleo": 65, "workday": 70, "lever": 75
            })
            st.markdown(_compat_grid(compat), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Overall assessment
            overall = result.get("overall_assessment", "")
            if overall:
                st.markdown(f"""
                <div class="card" style="margin-top:0">
                    <div class="card-title">UZMAN DEĞERLENDİRMESİ</div>
                    <p style="font-size:0.85rem;color:var(--text-secondary);line-height:1.7;margin:0">{overall}</p>
                </div>
                """, unsafe_allow_html=True)

    # ── Match Modu Sonuç ──────────────────────────────────────────────────────
    else:
        match_score = result.get("match_score", 0)
        color       = _score_color(match_score)
        verdict     = result.get("verdict", "")
        kw_gap      = prog.get("keyword_gap", {})

        col_ring, col_subs = st.columns([1, 2])

        with col_ring:
            st.markdown(_score_ring(match_score, "EŞLEŞİM SKORU"), unsafe_allow_html=True)
            st.markdown(f"""
            <div class="verdict-badge" style="background:rgba({
                '34,197,94' if match_score>=75 else '245,158,11' if match_score>=55 else '239,68,68'
            },0.1);border:1px solid {color}40;color:{color}">
                {verdict}
            </div>
            """, unsafe_allow_html=True)

        with col_subs:
            kw_score = kw_gap.get("keyword_score", 0)
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">KEYWORD GAP ANALİZİ</div>', unsafe_allow_html=True)
            st.markdown(
                _subscore_bar(f"Keyword Eşleşme ({kw_gap.get('total_matched',0)}/{kw_gap.get('total_required',0)})", kw_score, "🔑") +
                _subscore_bar("Bölüm Yapısı",    scores["section_score"], "📋") +
                _subscore_bar("Format Uyumu",    scores["format_score"],  "📐") +
                _subscore_bar("İletişim Bilgisi", scores["contact_score"], "📬"),
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # Keyword gap chips
        col_matched, col_missing = st.columns(2)

        with col_matched:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-title">✓ EŞLEŞEN TEKNİK BECERİLER ({len(kw_gap.get("matched_tech", []))})</div>', unsafe_allow_html=True)
            st.markdown(_chips(kw_gap.get("matched_tech", []), "chip-green"), unsafe_allow_html=True)
            st.markdown('<div class="card-title" style="margin-top:16px">✓ EŞLEŞEN SOFT SKILLS</div>', unsafe_allow_html=True)
            st.markdown(_chips(kw_gap.get("matched_soft", []), "chip-teal"), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_missing:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-title">✗ EKSİK TEKNİK BECERİLER ({len(kw_gap.get("missing_tech", []))})</div>', unsafe_allow_html=True)
            st.markdown(_chips(kw_gap.get("missing_tech", []), "chip-red"), unsafe_allow_html=True)
            st.markdown('<div class="card-title" style="margin-top:16px">✗ EKSİK SOFT SKILLS</div>', unsafe_allow_html=True)
            st.markdown(_chips(kw_gap.get("missing_soft", []), "chip-amber"), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Güçlü/Zayıf yönler
        col_str, col_weak = st.columns(2)

        with col_str:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">💪 GÜÇLÜ YÖNLER</div>', unsafe_allow_html=True)
            for s in result.get("strengths", []):
                st.markdown(f"""
                <div style="display:flex;gap:8px;padding:8px 0;border-bottom:1px solid #1E2235;
                            font-size:0.84rem;color:var(--text-primary);align-items:flex-start">
                    <span style="color:#22C55E;flex-shrink:0">✓</span><span>{s}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_weak:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">⚠ ZAYIF YÖNLER</div>', unsafe_allow_html=True)
            for w in result.get("weaknesses", []):
                st.markdown(f"""
                <div style="display:flex;gap:8px;padding:8px 0;border-bottom:1px solid #1E2235;
                            font-size:0.84rem;color:var(--text-primary);align-items:flex-start">
                    <span style="color:#EF4444;flex-shrink:0">✗</span><span>{w}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Öneriler
        recs = result.get("recommendations", [])
        if recs:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">ÖNCELİKLİ ÖNERİLER</div>', unsafe_allow_html=True)
            for rec in recs:
                st.markdown(_rec_card(rec), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Keyword önerileri + tailoring tips
        col_ks, col_tt = st.columns(2)
        with col_ks:
            ks = result.get("keyword_suggestions", "")
            if ks:
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">KEYWORD OPTİMİZASYONU</div>
                    <p style="font-size:0.84rem;color:var(--text-secondary);line-height:1.7;margin:0">{ks}</p>
                </div>
                """, unsafe_allow_html=True)
        with col_tt:
            tt = result.get("tailoring_tips", "")
            if tt:
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">POZİSYONA ÖZEL TAVSİYELER</div>
                    <p style="font-size:0.84rem;color:var(--text-secondary);line-height:1.7;margin:0">{tt}</p>
                </div>
                """, unsafe_allow_html=True)

        # Overall
        overall = result.get("overall_assessment", "")
        if overall:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">UZMAN DEĞERLENDİRMESİ</div>
                <p style="font-size:0.85rem;color:var(--text-secondary);line-height:1.7;margin:0">{overall}</p>
            </div>
            """, unsafe_allow_html=True)

    # ── Yeni analiz butonu ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↺  Yeni Analiz", use_container_width=False):
        st.session_state.result   = None
        st.session_state.analyzed = False
        st.rerun()
