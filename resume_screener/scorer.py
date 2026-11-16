"""Compare resumes with a job description and rank them.

Final score (0-100) = 50% skill match + 35% text similarity + 15% experience fit.
Every part of the score is returned so the result is easy to explain in a viva.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .skills import extract_skills

WEIGHTS = {"skills": 0.50, "similarity": 0.35, "experience": 0.15}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b|\+?\d[\d\s-]{8,}\d")
YEARS_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)", re.I)


@dataclass
class CandidateResult:
    filename: str
    name: str
    email: str | None
    phone: str | None
    score: float
    skill_score: float
    similarity_score: float
    experience_score: float
    years_experience: float
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    extra_skills: list[str] = field(default_factory=list)
    verdict: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def guess_name(text: str, filename: str) -> str:
    """Use the first short line without digits or @ as the candidate name."""
    for line in text.splitlines()[:5]:
        line = line.strip()
        if 2 <= len(line.split()) <= 4 and not re.search(r"[\d@:/|]", line):
            return line.title()
    return filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()


def years_of_experience(text: str) -> float:
    """Largest 'N years' value mentioned (0 when none)."""
    values = [float(v) for v in YEARS_RE.findall(text)]
    return max(values) if values else 0.0


def text_similarity(job_text: str, resume_texts: list[str]) -> list[float]:
    """TF-IDF cosine similarity of each resume against the job description."""
    if not resume_texts:
        return []
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    matrix = vectorizer.fit_transform([job_text, *resume_texts])
    return cosine_similarity(matrix[0:1], matrix[1:]).flatten().tolist()


def verdict_for(score: float) -> str:
    if score >= 70:
        return "Strong match"
    if score >= 50:
        return "Good match"
    if score >= 30:
        return "Partial match"
    return "Weak match"


def screen_resumes(job_text: str, resumes: dict[str, str]) -> list[CandidateResult]:
    """Score every resume ({filename: text}) and return them best first."""
    if not job_text.strip():
        raise ValueError("The job description is empty.")

    job_skills = extract_skills(job_text)
    required_years = years_of_experience(job_text)
    names = list(resumes)
    similarities = text_similarity(job_text, [resumes[n] for n in names])

    # Raw cosine values for short documents are small, so scale them so the
    # best resume in the batch can reach a sensible range (cap at 1.0).
    sim_scale = 1 / 0.6

    results = []
    for filename, similarity in zip(names, similarities):
        text = resumes[filename]
        skills = extract_skills(text)
        matched = sorted(job_skills & skills)
        missing = sorted(job_skills - skills)
        extra = sorted(skills - job_skills)

        skill_score = len(matched) / len(job_skills) if job_skills else similarity
        similarity_score = min(similarity * sim_scale, 1.0)
        years = years_of_experience(text)
        experience_score = 1.0 if required_years == 0 else min(years / required_years, 1.0)

        total = 100 * (
            WEIGHTS["skills"] * skill_score
            + WEIGHTS["similarity"] * similarity_score
            + WEIGHTS["experience"] * experience_score
        )
        email = EMAIL_RE.search(text)
        phone = PHONE_RE.search(text)
        results.append(
            CandidateResult(
                filename=filename,
                name=guess_name(text, filename),
                email=email.group(0) if email else None,
                phone=phone.group(0).strip() if phone else None,
                score=round(total, 1),
                skill_score=round(100 * skill_score, 1),
                similarity_score=round(100 * similarity_score, 1),
                experience_score=round(100 * experience_score, 1),
                years_experience=years,
                matched_skills=matched,
                missing_skills=missing,
                extra_skills=extra,
                verdict=verdict_for(total),
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results
