# analyzer.py — Hybrid ATS analizi: Programmatic + LLM
#
# Strateji:
#   1. cv_utils.py programmatic analizi (bölüm tespiti, keyword tarama,
#      format kontrolü, iletişim eksiksizliği) → nesnel alt skorlar
#   2. LLM (llama-3.3-70b-versatile) semantik analizi → programmatic
#      sonuçları bağlam olarak vererek gereksiz halüsinasyonu önleme
#   3. Structured JSON output → app.py'de zengin UI rendering

import re
import os
import json
import logging
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
logger  = logging.getLogger(__name__)
_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY ortam değişkeni ayarlı değil.")
        _client = Groq(api_key=api_key)
    return _client


def _safe_json(raw: str, fallback: dict) -> dict:
    """LLM çıktısından JSON'u güvenle parse et."""
    # Önce doğrudan parse dene
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    # Markdown code block içinden çıkar
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Ham JSON bloğunu bul
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    logger.warning("JSON parse başarısız, fallback kullanılıyor")
    return fallback


# ── ATS Analizi ──────────────────────────────────────────────────────────────

def analyze_ats(cv_text: str, programmatic: dict) -> dict:
    """
    Genel ATS analizi — iş ilanı olmadan.
    programmatic: compute_programmatic_ats_score + section/contact/keyword sonuçları
    """
    scores   = programmatic.get("scores",   {})
    sections = programmatic.get("sections", {})
    contact  = programmatic.get("contact",  {})
    keywords = programmatic.get("keywords", {})
    pdf_meta = programmatic.get("pdf_meta", {})

    found_sections   = [s for s, v in sections.items() if v]
    missing_sections = [s for s, v in sections.items() if not v]

    prompt = f"""You are a senior ATS (Applicant Tracking System) specialist with expertise in Greenhouse, Taleo, Workday, Lever, and iCIMS. Analyze this CV with precision.

=== PROGRAMMATIC SCAN RESULTS (objective data) ===
Scores:
  - Section completeness: {scores.get('section_score', 'N/A')}/100
  - Contact completeness: {scores.get('contact_score', 'N/A')}/100
  - Format compatibility:  {scores.get('format_score', 'N/A')}/100
  - Keyword strength:      {scores.get('keyword_score', 'N/A')}/100
  - Programmatic total:    {scores.get('total', 'N/A')}/100

Sections detected: {', '.join(found_sections) if found_sections else 'None'}
Sections missing:  {', '.join(missing_sections) if missing_sections else 'None'}

Tech skills found ({len(keywords.get('tech_skills', []))} total): {', '.join(keywords.get('tech_skills', [])[:12])}
Impact verbs found ({len(keywords.get('impact_verbs', []))} total): {', '.join(keywords.get('impact_verbs', [])[:8])}
Keyword density: {keywords.get('keyword_density', 0):.1f}% (ideal range: 1–3%)
Word count: {pdf_meta.get('word_count', 'N/A')} (ideal: 400–800)
Page count: {pdf_meta.get('page_count', 'N/A')} (ideal: 1–2)
Multi-column layout: {pdf_meta.get('has_columns', False)}
Contains images: {pdf_meta.get('has_images', False)}

Contact info: email={bool(contact.get('email'))}, phone={bool(contact.get('phone'))}, linkedin={bool(contact.get('linkedin'))}, github={bool(contact.get('github'))}
Format penalties: {', '.join(scores.get('format_penalties', [])) or 'None'}

=== YOUR TASK ===
Provide expert qualitative analysis that COMPLEMENTS the programmatic scan above.
Focus on: semantic quality, impact language, career narrative, content depth.
Be STRICT and HONEST — do not inflate scores.

Return ONLY valid JSON (no markdown, no explanation before/after):
{{
  "ats_score": <integer 0-100, your holistic assessment>,
  "verdict": "<one punchy line in Turkish, e.g. 'ATS'i geçer ama recruiter'ı etkilemez'>",
  "section_feedback": "<Turkish: section structure quality assessment>",
  "keyword_feedback": "<Turkish: keyword usage, density, and relevance assessment>",
  "contact_feedback": "<Turkish: contact info completeness assessment>",
  "format_issues": [
    "<specific formatting problem that hurts ATS parsing>"
  ],
  "quick_wins": [
    "<high-impact fix #1 — be concrete, e.g. 'Skills bölümüne Python, SQL, Docker ekle'>",
    "<high-impact fix #2>",
    "<high-impact fix #3>"
  ],
  "content_tips": [
    "<tip to improve content quality, e.g. 'Her iş deneyimine rakam ekle: %15 maliyet düşürdüm'>",
    "<tip 2>",
    "<tip 3>"
  ],
  "ats_compatibility": {{
    "greenhouse": <int 40-100>,
    "taleo":      <int 40-100>,
    "workday":    <int 40-100>,
    "lever":      <int 40-100>
  }},
  "overall_assessment": "<3-4 sentence expert summary in Turkish>"
}}

=== CV TEXT ===
{cv_text[:3500]}
"""

    fallback = {
        "ats_score":         scores.get("total", 50),
        "verdict":           "Analiz tamamlandı",
        "section_feedback":  "",
        "keyword_feedback":  "",
        "contact_feedback":  "",
        "format_issues":     scores.get("format_penalties", []),
        "quick_wins":        [],
        "content_tips":      [],
        "ats_compatibility": {"greenhouse": 65, "taleo": 60, "workday": 65, "lever": 70},
        "overall_assessment": "LLM analizi tamamlanamadı. Programmatic skorlar geçerlidir.",
    }

    try:
        resp = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=1800,
        )
        raw = resp.choices[0].message.content.strip()
        return _safe_json(raw, fallback)
    except Exception as e:
        logger.error(f"ATS LLM analizi başarısız: {e}")
        return fallback


# ── CV vs İş İlanı Karşılaştırma ────────────────────────────────────────────

def analyze_cv(cv_text: str, job_text: str, programmatic: dict) -> dict:
    """
    CV ile iş ilanını karşılaştır.
    programmatic: keyword_gap + scores sonuçları
    """
    gap    = programmatic.get("keyword_gap",  {})
    scores = programmatic.get("scores",       {})

    matched_tech = gap.get("matched_tech", [])
    missing_tech = gap.get("missing_tech", [])
    matched_soft = gap.get("matched_soft", [])
    missing_soft = gap.get("missing_soft", [])
    kw_score     = gap.get("keyword_score", 0)

    prompt = f"""You are a senior recruiter and ATS expert. Compare this CV against the job description with extreme precision.

=== PROGRAMMATIC KEYWORD ANALYSIS ===
Keyword match score: {kw_score}% ({gap.get('total_matched', 0)}/{gap.get('total_required', 0)} keywords)

Matched tech skills: {', '.join(matched_tech) if matched_tech else 'None'}
Missing tech skills: {', '.join(missing_tech) if missing_tech else 'None'}
Matched soft skills: {', '.join(matched_soft) if matched_soft else 'None'}
Missing soft skills: {', '.join(missing_soft) if missing_soft else 'None'}

Programmatic scores → sections: {scores.get('section_score','N/A')}, format: {scores.get('format_score','N/A')}, contact: {scores.get('contact_score','N/A')}

=== YOUR TASK ===
Go BEYOND simple keyword matching. Assess:
- Seniority/experience level alignment
- Industry relevance
- Cultural fit signals
- Career trajectory alignment
- Achievement quality vs. job expectations

Scoring guide (be strict):
  80–100: Strong match — apply immediately
  60–79:  Good match — minor tailoring needed
  40–59:  Moderate match — significant gaps
  0–39:   Weak match — major restructuring needed

Return ONLY valid JSON:
{{
  "match_score": <integer 0-100>,
  "verdict": "<one punchy verdict in Turkish>",
  "strengths": [
    "<strength 1: specific CV element that strongly matches job>",
    "<strength 2>",
    "<strength 3>"
  ],
  "weaknesses": [
    "<weakness 1: specific gap between CV and job>",
    "<weakness 2>",
    "<weakness 3>"
  ],
  "recommendations": [
    {{"priority": "high",   "action": "<concrete CV edit>", "reason": "<why it matters for this job>"}},
    {{"priority": "high",   "action": "<concrete CV edit>", "reason": "<why>"}},
    {{"priority": "medium", "action": "<concrete CV edit>", "reason": "<why>"}},
    {{"priority": "low",    "action": "<nice-to-have>",     "reason": "<why>"}}
  ],
  "keyword_suggestions": "<2-3 sentences in Turkish on how to incorporate missing keywords naturally>",
  "tailoring_tips": "<2-3 sentences in Turkish on how to tailor the CV specifically for this role>",
  "overall_assessment": "<3-4 sentence expert assessment in Turkish>"
}}

=== CV ===
{cv_text[:2800]}

=== JOB DESCRIPTION ===
{job_text[:2000]}
"""

    fallback = {
        "match_score":        kw_score,
        "verdict":            "Analiz tamamlandı",
        "strengths":          [],
        "weaknesses":         [],
        "recommendations":    [],
        "keyword_suggestions": "",
        "tailoring_tips":     "",
        "overall_assessment": "LLM analizi tamamlanamadı. Keyword skoru geçerlidir.",
    }

    try:
        resp = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        return _safe_json(raw, fallback)
    except Exception as e:
        logger.error(f"CV karşılaştırma LLM analizi başarısız: {e}")
        return fallback
