# cv_utils.py — PDF parsing, section detection, programmatic ATS analysis
#
# ATS Araştırması Özeti (2025):
#   - Keywords: Toplam skorun %35-40'ı
#   - Section detection: %25 (Experience, Education, Skills kritik)
#   - Format: %20 (kolon, grafik, sayfa sayısı, kelime yoğunluğu)
#   - Contact completeness: %20 (email, telefon, LinkedIn)
#   - Keyword yoğunluğu ideali: %1-3

import re
import fitz
import requests
from bs4 import BeautifulSoup

# ── ATS Standart Bölüm Başlıkları ───────────────────────────────────────────
SECTION_PATTERNS = {
    "contact":        r"\b(contact|iletişim|kişisel bilgi|personal info|bilgilerim)\b",
    "summary":        r"\b(summary|objective|profile|about me|özet|hakkımda|profil|hedef)\b",
    "experience":     r"\b(experience|work history|employment|deneyim|iş deneyimi|kariyer|çalışma)\b",
    "education":      r"\b(education|academic|degree|eğitim|mezuniyet|öğrenim|akademik)\b",
    "skills":         r"\b(skills|technical skills|competencies|beceriler|yetenekler|yetkinlikler|teknik)\b",
    "certifications": r"\b(certif|license|credential|sertifika|lisans|belge)\b",
    "projects":       r"\b(project|portfolio|proje|portföy|çalışmalar)\b",
    "languages":      r"\b(language|dil|yabancı dil)\b",
    "awards":         r"\b(award|honor|achievement|ödül|başarı|onur)\b",
    "volunteer":      r"\b(volunteer|gönüllü|staj|internship)\b",
}

# ── Teknik Beceri Bankası ────────────────────────────────────────────────────
TECH_SKILLS = {
    # Diller
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "php", "ruby", "scala", "r", "matlab",
    # Frontend
    "react", "angular", "vue", "next.js", "nuxt", "svelte",
    "html", "css", "sass", "tailwind", "bootstrap", "webpack",
    # Backend
    "node.js", "django", "flask", "fastapi", "spring", "express",
    "laravel", ".net", "graphql", "rest api", "microservices",
    # Veritabanı
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "sqlite", "oracle", "cassandra", "dynamodb",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "ci/cd", "jenkins", "github actions", "gitlab", "linux", "bash",
    # Veri & ML
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "xgboost",
    "pandas", "numpy", "spark", "hadoop", "kafka", "airflow",
    "power bi", "tableau", "data analysis", "data science", "statistics",
    # Araçlar
    "git", "jira", "confluence", "figma", "postman", "swagger",
    "agile", "scrum", "devops", "excel",
}

# ── Soft Skills Bankası ──────────────────────────────────────────────────────
SOFT_SKILLS = {
    "leadership", "communication", "teamwork", "problem solving",
    "critical thinking", "project management", "time management",
    "collaboration", "adaptability", "creativity", "analytical",
    "attention to detail", "presentation", "mentoring", "negotiation",
    "liderlik", "iletişim", "takım çalışması", "problem çözme",
    "proje yönetimi", "zaman yönetimi", "analitik düşünce",
}

# ── Etki Fiilleri (Impact Verbs) — ATS skoru artırır ────────────────────────
IMPACT_VERBS = {
    "achieved", "improved", "led", "managed", "developed", "created",
    "built", "launched", "increased", "reduced", "saved", "generated",
    "delivered", "designed", "implemented", "optimized", "transformed",
    "accelerated", "spearheaded", "orchestrated", "streamlined", "deployed",
    "architected", "automated", "scaled", "negotiated", "mentored",
    "geliştirdi", "oluşturdu", "yönetti", "artırdı", "azalttı", "tasarladı",
    "uyguladı", "başlattı", "optimize etti", "otomatize etti",
}

# ── İletişim Bilgisi Pattern'leri ────────────────────────────────────────────
CONTACT_PATTERNS = {
    "email":    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "phone":    r"(\+?\d[\d\s\-().]{7,}\d)",
    "linkedin": r"linkedin\.com/in/[\w\-]+",
    "github":   r"github\.com/[\w\-]+",
    "website":  r"https?://(?!linkedin|github)[\w.\-/]+",
}


# ── PDF Okuma ────────────────────────────────────────────────────────────────

def extract_pdf_full(uploaded_file) -> dict:
    """
    PDF'ten hem metni hem yapısal metadata'yı tek seferde çıkar.
    Streamlit'te dosya ikinci kez okunamazsa seek(0) kullan.
    """
    try:
        uploaded_file.seek(0)
    except AttributeError:
        pass

    raw_bytes = uploaded_file.read()
    doc = fitz.open(stream=raw_bytes, filetype="pdf")

    full_text = ""
    has_columns = False
    has_images  = False

    for page in doc:
        full_text += page.get_text()

        # Kolon tespiti: bloklar yatayda >200px arayla dizilmişse çok kolonlu
        blocks = page.get_text("blocks")
        if len(blocks) > 3:
            x_coords = [b[0] for b in blocks]
            if max(x_coords) - min(x_coords) > 200:
                has_columns = True

        # Görsel / fotoğraf tespiti
        if page.get_images():
            has_images = True

    page_count = doc.page_count   # ← close'dan ÖNCE kaydet
    doc.close()
    
    return {
        "text":       full_text.strip(),
        "page_count": doc.page_count,
        "has_columns": has_columns,
        "has_images":  has_images,
        "char_count":  len(full_text),
        "word_count":  len(full_text.split()),
    }


# ── Bölüm Tespiti ────────────────────────────────────────────────────────────

def detect_sections(text: str) -> dict:
    """Hangi standart ATS bölümlerinin mevcut olduğunu tespit et."""
    text_lower = text.lower()
    return {
        section: bool(re.search(pattern, text_lower, re.IGNORECASE))
        for section, pattern in SECTION_PATTERNS.items()
    }


# ── İletişim Bilgisi Tespiti ─────────────────────────────────────────────────

def detect_contact_info(text: str) -> dict:
    """İletişim bilgilerinin eksiksizliğini kontrol et."""
    results = {}
    for field, pattern in CONTACT_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        results[field] = match.group(0) if match else None
    return results


# ── Keyword Çıkarma ──────────────────────────────────────────────────────────

def extract_keywords_from_text(text: str) -> dict:
    """CV metninden teknik beceri, soft skill ve etki fiillerini çıkar."""
    text_lower = text.lower()
    word_count  = len(text.split())

    found_tech   = [s for s in TECH_SKILLS   if s in text_lower]
    found_soft   = [s for s in SOFT_SKILLS   if s in text_lower]
    found_impact = [v for v in IMPACT_VERBS  if v in text_lower]

    # Keyword yoğunluğu: toplam keyword / toplam kelime
    density = (len(found_tech) + len(found_soft)) / max(word_count, 1) * 100

    return {
        "tech_skills":      sorted(found_tech),
        "soft_skills":      sorted(found_soft),
        "impact_verbs":     sorted(found_impact),
        "keyword_density":  round(density, 2),
        "word_count":       word_count,
    }


def extract_keywords_from_job(job_text: str) -> dict:
    """İş ilanından gerekli keyword'leri çıkar."""
    text_lower = job_text.lower()
    return {
        "tech_skills": sorted(s for s in TECH_SKILLS  if s in text_lower),
        "soft_skills": sorted(s for s in SOFT_SKILLS  if s in text_lower),
    }


def compute_keyword_gap(cv_kw: dict, job_kw: dict) -> dict:
    """CV ile iş ilanı arasındaki keyword farkını hesapla."""
    cv_tech  = set(cv_kw["tech_skills"])
    cv_soft  = set(cv_kw["soft_skills"])
    job_tech = set(job_kw["tech_skills"])
    job_soft = set(job_kw["soft_skills"])

    matched_tech = sorted(cv_tech & job_tech)
    missing_tech = sorted(job_tech - cv_tech)
    matched_soft = sorted(cv_soft & job_soft)
    missing_soft = sorted(job_soft - cv_soft)

    total    = len(job_tech) + len(job_soft)
    matched  = len(matched_tech) + len(matched_soft)
    kw_score = round((matched / max(total, 1)) * 100)

    return {
        "matched_tech":  matched_tech,
        "missing_tech":  missing_tech,
        "matched_soft":  matched_soft,
        "missing_soft":  missing_soft,
        "keyword_score": kw_score,
        "total_required": total,
        "total_matched":  matched,
    }


# ── Programmatic ATS Skoru ───────────────────────────────────────────────────

def compute_programmatic_ats_score(pdf_meta: dict, sections: dict,
                                    contact: dict, keywords: dict) -> dict:
    """
    ATS araştırmasına dayalı ağırlıklı skor hesabı:
      Sections  : %25  (Experience, Education, Skills kritik; diğerleri bonus)
      Contact   : %20  (email, telefon, LinkedIn, GitHub)
      Format    : %20  (sayfa sayısı, kolonlar, görseller, kelime sayısı)
      Keywords  : %35  (teknik beceriler + etki fiilleri + yoğunluk)
    """
    # — Bölüm skoru (%25) —
    critical = ["experience", "education", "skills"]
    bonus    = ["summary", "certifications", "projects", "contact", "languages"]
    c_found  = sum(1 for s in critical if sections.get(s))
    b_found  = sum(1 for s in bonus    if sections.get(s))
    section_score = round((c_found / len(critical)) * 75 + (b_found / len(bonus)) * 25)

    # — İletişim skoru (%20) —
    contact_score = 0
    if contact.get("email"):    contact_score += 40
    if contact.get("phone"):    contact_score += 30
    if contact.get("linkedin"): contact_score += 20
    if contact.get("github") or contact.get("website"): contact_score += 10

    # — Format skoru (%20) —
    format_score = 100
    penalties = []
    if pdf_meta["has_columns"]:
        format_score -= 20
        penalties.append("Çok kolonlu düzen: eski ATS sistemleri okuyamaz")
    if pdf_meta["has_images"]:
        format_score -= 15
        penalties.append("Görsel/fotoğraf: ATS parse hatası oluşturabilir")
    if pdf_meta["page_count"] > 2:
        format_score -= 10
        penalties.append(f"{pdf_meta['page_count']} sayfa: ATS için ideal 1-2 sayfa")
    wc = pdf_meta["word_count"]
    if wc < 150:
        format_score -= 30
        penalties.append(f"Çok az içerik ({wc} kelime): ATS düşük skor verir")
    elif wc < 250:
        format_score -= 15
        penalties.append(f"Az içerik ({wc} kelime): ideal 400-800 kelime")
    elif wc > 1000:
        format_score -= 10
        penalties.append(f"Çok fazla içerik ({wc} kelime): özetle")
    format_score = max(format_score, 0)

    # — Keyword skoru (%35) —
    tc   = len(keywords["tech_skills"])
    ic   = len(keywords["impact_verbs"])
    dens = keywords["keyword_density"]
    kw_score = min(tc * 5, 55) + min(ic * 4, 35)
    if 1.0 <= dens <= 3.0:
        kw_score += 10  # ideal yoğunluk bonusu
    kw_score = min(kw_score, 100)

    # — Ağırlıklı toplam —
    total = round(
        section_score * 0.25 +
        contact_score * 0.20 +
        format_score  * 0.20 +
        kw_score      * 0.35
    )

    return {
        "total":         total,
        "section_score": section_score,
        "contact_score": contact_score,
        "format_score":  format_score,
        "keyword_score": kw_score,
        "format_penalties": penalties,
    }


# ── İş İlanı Çekme ───────────────────────────────────────────────────────────

def extract_job_posting(url: str) -> str:
    """URL'den iş ilanı metnini çek ve temizle."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        lines = [
            line.strip()
            for line in soup.get_text(separator="\n").splitlines()
            if line.strip() and len(line.strip()) > 3
        ]
        return "\n".join(lines[:400])
    except Exception:
        return ""
