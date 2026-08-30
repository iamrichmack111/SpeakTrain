#!/usr/bin/env python3
"""Fail CI when public documentation or icon-based D2 sources are incomplete."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_WIKI = {
    "Home.md", "Getting-Started.md", "Today-Dashboard.md", "Phrase-Practice.md",
    "Courses-and-Mastery.md", "OPI-Simulator.md", "Vocabulary-Test.md",
    "Conjugation-Drill.md", "Guided-Conversation.md",
    "Vocabulary-and-Sentence-Lab.md", "Progress-and-Reports.md",
    "Admin-and-Curriculum-Studio.md", "Proficiency-Roadmap.md",
    "Docker-and-Deployment.md", "Testing-and-CI-CD.md", "Architecture.md",
}


def main():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for required in ("Quick start", "Requirements", "Docker", "Playwright", "Proficiency", "Wiki"):
        assert required.lower() in readme.lower(), f"README is missing {required}"
    wiki_dir = ROOT / "wiki"
    present = {path.name for path in wiki_dir.glob("*.md")}
    assert REQUIRED_WIKI <= present, f"Missing Wiki pages: {sorted(REQUIRED_WIKI - present)}"
    for diagram in (ROOT / "docs" / "diagrams").glob("*.d2"):
        text = diagram.read_text(encoding="utf-8")
        nodes = [line.strip() for line in text.splitlines() if ":" in line and "{" in line and "class:" in line and "classes:" not in line]
        assert nodes, f"No nodes detected in {diagram.name}"
        assert all("icon:" in line for line in nodes), f"Every D2 node needs an icon: {diagram.name}"
    screenshot_spec = (ROOT / "tests" / "e2e" / "screenshots.spec.js").read_text(encoding="utf-8")
    assert screenshot_spec.count(".png'") >= 12, "Expected at least twelve Playwright documentation screenshots"
    print("Documentation validation passed: README, Wiki, D2 icons, and screenshot coverage")


if __name__ == "__main__":
    main()
