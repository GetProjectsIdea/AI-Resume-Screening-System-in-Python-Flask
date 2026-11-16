"""Flask web app for the AI Resume Screening & Job Match System."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path

from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, url_for)

from resume_screener import __version__
from resume_screener import database as db
from resume_screener.extractor import (SUPPORTED_EXTENSIONS,
                                       UnsupportedFileError,
                                       extract_text_from_bytes)
from resume_screener.scorer import WEIGHTS, screen_resumes

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASE_DIR / "sample_data"


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "change-me-in-production"),
        DATABASE=str(Path(app.instance_path) / "screenings.sqlite3"),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10 MB per request
        MAX_RESUMES=25,
    )
    if config:
        app.config.update(config)

    @app.context_processor
    def inject_globals():
        return {"version": __version__, "weights": WEIGHTS}

    @app.get("/")
    def index():
        return render_template("index.html", extensions=", ".join(sorted(SUPPORTED_EXTENSIONS)))

    @app.post("/screen")
    def screen():
        job_title = request.form.get("job_title", "").strip() or "Untitled role"
        job_text = request.form.get("job_description", "").strip()
        files = [f for f in request.files.getlist("resumes") if f and f.filename]

        if not job_text:
            flash("Please paste the job description.", "error")
            return redirect(url_for("index"))
        if not files:
            flash("Please upload at least one resume.", "error")
            return redirect(url_for("index"))
        if len(files) > app.config["MAX_RESUMES"]:
            flash(f"You can upload up to {app.config['MAX_RESUMES']} resumes at a time.", "error")
            return redirect(url_for("index"))

        resumes, skipped = {}, []
        for f in files:
            try:
                text = extract_text_from_bytes(f.read(), f.filename)
            except UnsupportedFileError:
                skipped.append(f.filename)
                continue
            except Exception:  # damaged or password-protected file
                skipped.append(f.filename)
                continue
            if text:
                resumes[f.filename] = text
            else:
                skipped.append(f.filename)

        if skipped:
            flash("Skipped (unreadable or unsupported): " + ", ".join(skipped), "warning")
        if not resumes:
            return redirect(url_for("index"))

        results = [r.to_dict() for r in screen_resumes(job_text, resumes)]
        screening_id = db.save_screening(app.config["DATABASE"], job_title, job_text, results)
        return redirect(url_for("results", screening_id=screening_id))

    @app.post("/demo")
    def demo():
        """Run the bundled sample job description and resumes in one click."""
        job_text = (SAMPLE_DIR / "job_description.txt").read_text(encoding="utf-8")
        resumes = {p.name: p.read_text(encoding="utf-8")
                   for p in sorted((SAMPLE_DIR / "resumes").glob("*.txt"))}
        results = [r.to_dict() for r in screen_resumes(job_text, resumes)]
        screening_id = db.save_screening(app.config["DATABASE"], "Python Developer (Sample)", job_text, results)
        return redirect(url_for("results", screening_id=screening_id))

    @app.get("/results/<int:screening_id>")
    def results(screening_id: int):
        screening = db.get_screening(app.config["DATABASE"], screening_id)
        if screening is None:
            abort(404)
        return render_template("results.html", s=screening)

    @app.get("/results/<int:screening_id>/csv")
    def export_csv(screening_id: int):
        screening = db.get_screening(app.config["DATABASE"], screening_id)
        if screening is None:
            abort(404)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Rank", "Name", "Email", "Phone", "File", "Score", "Verdict",
                         "Skill %", "Similarity %", "Experience %", "Matched Skills", "Missing Skills"])
        for rank, r in enumerate(screening["results"], start=1):
            writer.writerow([rank, r["name"], r["email"] or "", r["phone"] or "", r["filename"],
                             r["score"], r["verdict"], r["skill_score"], r["similarity_score"],
                             r["experience_score"], ", ".join(r["matched_skills"]),
                             ", ".join(r["missing_skills"])])
        return Response(buf.getvalue(), mimetype="text/csv", headers={
            "Content-Disposition": f"attachment; filename=screening-{screening_id}.csv"})

    @app.get("/history")
    def history():
        return render_template("history.html", screenings=db.list_screenings(app.config["DATABASE"]))

    @app.post("/history/<int:screening_id>/delete")
    def delete(screening_id: int):
        db.delete_screening(app.config["DATABASE"], screening_id)
        flash("Screening deleted.", "success")
        return redirect(url_for("history"))

    @app.errorhandler(413)
    def too_large(_):
        flash("Upload is too large. Keep the total under 10 MB.", "error")
        return redirect(url_for("index"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
