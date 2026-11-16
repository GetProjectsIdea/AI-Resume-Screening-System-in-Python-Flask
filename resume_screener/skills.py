"""Find known skills in a piece of text using a JSON skills dictionary."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DEFAULT_SKILLS_FILE = Path(__file__).resolve().parent.parent / "data" / "skills.json"

# Skill names that are also everyday words or single letters. For these we only
# trust the aliases in skills.json (e.g. "golang"), never the bare name.
AMBIGUOUS_NAMES = {"r", "c", "go"}

# Knowing one skill proves another (someone who uses MySQL knows SQL).
IMPLIED_SKILLS = {
    "MySQL": "SQL",
    "PostgreSQL": "SQL",
    "SQLite": "SQL",
    "Django": "Python",
    "Flask": "Python",
    "FastAPI": "Python",
    "Next.js": "React",
    "Express.js": "Node.js",
}


@lru_cache(maxsize=4)
def load_skills(path: str | Path = DEFAULT_SKILLS_FILE) -> dict[str, list[str]]:
    """Load {"Skill Name": ["alias 1", "alias 2"]} from the JSON file."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    skills: dict[str, list[str]] = {}
    for category in data.values():
        for name, aliases in category.items():
            terms = {a.lower() for a in aliases}
            if name.lower() not in AMBIGUOUS_NAMES:
                terms.add(name.lower())
            skills[name] = sorted(terms, key=len, reverse=True)
    return skills


@lru_cache(maxsize=4)
def skill_categories(path: str | Path = DEFAULT_SKILLS_FILE) -> dict[str, str]:
    """Map every skill to its category, e.g. "Flask" -> "Web Frameworks"."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {name: category for category, items in data.items() for name in items}


def _alias_pattern(alias: str) -> re.Pattern[str]:
    # Word boundaries that also work for skills like "c++", "c#" or "node.js".
    return re.compile(r"(?<![a-z0-9+#])" + re.escape(alias) + r"(?![a-z0-9+#])")


def extract_skills(text: str, skills: dict[str, list[str]] | None = None) -> set[str]:
    """Return the set of skill names that appear anywhere in the text."""
    skills = skills or load_skills()
    lowered = text.lower()
    found = set()
    for name, aliases in skills.items():
        if any(_alias_pattern(alias).search(lowered) for alias in aliases):
            found.add(name)
    found |= {IMPLIED_SKILLS[s] for s in found if s in IMPLIED_SKILLS and IMPLIED_SKILLS[s] in skills}
    return found
