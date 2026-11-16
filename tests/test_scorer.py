import pytest

from resume_screener.scorer import guess_name, screen_resumes, years_of_experience
from resume_screener.skills import extract_skills


def test_skill_aliases_and_boundaries():
    skills = extract_skills("Worked with sklearn, ReactJS, node.js and golang. Excellent C++ and C# skills.")
    assert {"scikit-learn", "React", "Node.js", "Go", "C++", "C#"} <= skills
    assert "Excel" not in skills          # "Excellent" must not count as Excel
    assert "Java" not in extract_skills("JavaScript developer")
    assert "Go" not in extract_skills("Ready to go the extra mile")
    assert "R" not in extract_skills("R&D team")
    assert "SQL" in extract_skills("Built reports on PostgreSQL")  # implied skill


def test_years_and_name():
    assert years_of_experience("2 years at A, 1.5 yrs at B") == 2.0
    assert years_of_experience("no experience") == 0.0
    assert guess_name("Asha Rao\nasha@example.com", "a.txt") == "Asha Rao"
    assert guess_name("asha@example.com", "asha_rao.pdf") == "Asha Rao"


def test_ranking_on_sample_data(sample_dir):
    job = (sample_dir / "job_description.txt").read_text()
    resumes = {p.name: p.read_text() for p in (sample_dir / "resumes").glob("*.txt")}
    results = screen_resumes(job, resumes)

    assert [r.filename for r in results][0] == "aarav_sharma.txt"
    assert results[-1].filename in {"sneha_reddy.txt", "rohan_verma.txt"}
    assert all(0 <= r.score <= 100 for r in results)
    assert results == sorted(results, key=lambda r: r.score, reverse=True)

    top = results[0]
    assert "Flask" in top.matched_skills and "AWS" in top.missing_skills
    assert top.email == "aarav.sharma@example.com"
    assert top.verdict in {"Strong match", "Good match"}


def test_empty_job_description():
    with pytest.raises(ValueError):
        screen_resumes("   ", {"a.txt": "Python"})
