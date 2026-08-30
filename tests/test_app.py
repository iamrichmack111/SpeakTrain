import tempfile
from pathlib import Path

import pytest

from speaktrain import create_app
from speaktrain.content import all_phrases
from speaktrain.scoring import cipher_for, measured_wpm, score_words


@pytest.fixture()
def client():
    with tempfile.TemporaryDirectory() as directory:
        app = create_app({"TESTING": True, "DATABASE": str(Path(directory) / "test.sqlite3")})
        with app.test_client() as client:
            response = client.post("/register", data={"username": "tester", "password": "secret12"})
            assert response.status_code == 302
            yield client


def test_home_and_catalog(client):
    home = client.get("/")
    assert home.status_code == 200
    assert b"YOUR ADAPTIVE SESSION" in home.data
    assert b"Conjugation drill" in home.data
    assert b"GUIDED CONVERSATION" in home.data
    data = client.get("/api/catalog").get_json()
    assert {item["id"] for item in data["languages"]} == {"arabic", "spanish"}
    assert len(data["courses"]) == 4
    assert len(data["bridges"]) == 12
    assert any(item["id"] == "introductions" for item in data["languages"][0]["scenarios"])


def test_vocabulary_library_and_conjugations(client):
    lexicon = client.get("/api/catalog").get_json()["lexicon"]
    assert len(lexicon["vocabulary"]) >= 36
    assert sum(1 for item in lexicon["vocabulary"] if item["cognate"]) >= 10
    for language in ("spanish", "arabic"):
        builder = lexicon["builders"][language]
        people = {item["person"] for item in builder["subjects"]}
        assert len(builder["verbs"]) == 8
        for verb in builder["verbs"]:
            assert set(verb["conjugations"]["present"]) == people
            assert set(verb["conjugations"]["past"]) == people
            assert any(verb["id"] in item.get("verbs", []) for item in builder["complements"])


def test_manual_scoring_and_progress(client):
    response = client.post("/api/score", data={"phrase_id": "es-appt-01", "recognized": "Quisiera programar una cita"})
    assert response.status_code == 200
    assert response.get_json()["score"] == 100.0
    progress = client.get("/api/progress").get_json()
    assert progress["summary"]["attempts"] == 1
    assert progress["summary"]["average"] == 100.0


def test_gender_variant_and_wpm(client):
    response = client.post("/api/score", data={"phrase_id": "ar-house-01", "variant": "female", "recognized": "وينك", "duration": "1.5"})
    data = response.get_json()
    assert response.status_code == 200
    assert data["variant"] == "female"
    assert data["wpm"] is None
    catalog = client.get("/api/catalog").get_json()
    phrase = catalog["languages"][0]["scenarios"][0]["phrases"][0]
    assert phrase["variants"]["male"]["transliteration"] == "wēnak?"
    assert phrase["variants"]["female"]["transliteration"] == "wēnik?"


def test_vocabulary_and_profile(client):
    question = client.get("/api/vocabulary/question?language=spanish&mode=english_to_target").get_json()
    assert len(question["choices"]) == 4
    phrase = next(item[2] for item in all_phrases() if item[2]["id"] == question["phrase_id"])
    answer = client.post("/api/vocabulary/answer", json={"phrase_id": question["phrase_id"], "mode": question["mode"], "selected": phrase["target"]}).get_json()
    assert answer["correct"] is True
    assert answer["profile"]["xp"] >= 10


def test_formal_phrase_and_bridge_quiz(client):
    response = client.post("/api/score", data={"phrase_id": "es-intro-01", "register": "formal", "recognized": "Como se llama usted"})
    data = response.get_json()
    assert data["score"] == 100.0
    assert data["register"] == "formal"
    assert "usted" in data["expected"]
    question = client.get("/api/vocabulary/question?mode=spanish_to_arabic").get_json()
    assert question["quiz_type"] == "bridge"
    assert len(question["choices"]) == 4
    answer = client.post("/api/vocabulary/answer", json={"phrase_id": question["phrase_id"], "mode": question["mode"], "quiz_type": "bridge", "selected": question["choices"][0]})
    assert answer.status_code == 200
    assert "transliteration" in answer.get_json()


def test_course_gender_forms_and_response_transliteration(client):
    catalog = client.get("/api/catalog").get_json()
    arabic = next(item for item in catalog["languages"] if item["id"] == "arabic")
    introductions = next(item for item in arabic["scenarios"] if item["id"] == "introductions")
    phrase = next(item for item in introductions["phrases"] if item["id"] == "ar-intro-01")
    assert phrase["registers"]["informal"]["variants"]["male"]["transliteration"] == "shū ismak?"
    assert phrase["registers"]["informal"]["variants"]["female"]["transliteration"] == "shū ismik?"
    assert phrase["registers"]["formal"]["variants"]["male"]["target"] != phrase["registers"]["formal"]["variants"]["female"]["target"]
    assert phrase["responseTransliteration"]
    response = client.post("/api/score", data={"phrase_id": "ar-intro-01", "register": "informal", "variant": "female", "recognized": "شو اسمك"})
    assert response.status_code == 200
    assert response.get_json()["expected"] == "شو اسمِك؟"


def test_admin_and_printable_reports(client):
    page = client.get("/admin")
    assert page.status_code == 200
    assert b"Export all grades CSV" in page.data
    created = client.post("/admin/users", data={"username": "learner", "password": "secret34", "role": "student"})
    assert created.status_code == 302
    csv_response = client.get("/admin/grades.csv")
    assert csv_response.status_code == 200
    assert b"strengths,weaknesses,tips" in csv_response.data
    for period in ("daily", "weekly", "monthly"):
        report = client.get(f"/report/{period}")
        assert report.status_code == 200
        assert b"vocabulary sheet" in report.data


def test_adaptive_review_and_today_dashboard(client):
    today = client.get("/api/today")
    assert today.status_code == 200
    assert len(today.get_json()["items"]) >= 8
    result = client.post("/api/score", data={"phrase_id": "es-appt-01", "recognized": "Quisiera programar una cita"}).get_json()
    assert result["review"]["mastery_label"] == "Learning"
    refreshed = client.get("/api/today").get_json()
    assert len(refreshed["courses"]) == 4
    assert refreshed["mastery"]["1"] >= 1


def test_conjugation_and_conversation_drills(client):
    question = client.get("/api/conjugation/question?language=arabic&tense=present").get_json()
    catalog = client.get("/api/catalog").get_json()
    builder = catalog["lexicon"]["builders"]["arabic"]
    verb = next(item for item in builder["verbs"] if item["id"] == question["verb_id"])
    correct = verb["conjugations"][question["tense"]][question["person"]]["target"]
    answer = client.post("/api/conjugation/answer", json={**question, "selected": correct}).get_json()
    assert answer["correct"] is True
    assert answer["review"]["mastery"] == 1
    conversation = client.get("/api/conversation/question?language=spanish").get_json()
    phrase = next(item[2] for item in all_phrases() if item[2]["id"] == conversation["phrase_id"])
    conversation_answer = client.post("/api/conversation/answer", json={"phrase_id": phrase["id"], "selected": phrase["responseEnglish"]}).get_json()
    assert conversation_answer["correct"] is True
    assert conversation_answer["response"] == phrase["response"]


def test_admin_curriculum_editor(client):
    assert b"CURRICULUM STUDIO" in client.get("/admin").data
    phrase = client.post("/admin/phrases", data={
        "language": "arabic", "course": "foundations", "scenario": "Family custom",
        "english": "Welcome home.", "target": "أهلا بالبيت.", "transliteration": "ahla bil-bēt.",
        "formal_target": "مرحباً بك في المنزل.", "formal_transliteration": "marḥaban bika fī al-manzil.",
        "response": "الله يخلّيك.", "response_english": "Thank you.", "response_transliteration": "Allāh ykhallīk.",
    })
    assert phrase.status_code == 302
    catalog = client.get("/api/catalog").get_json()
    custom = [item for language in catalog["languages"] for scenario in language["scenarios"] for item in scenario["phrases"] if item.get("custom")]
    assert custom[0]["english"] == "Welcome home."
    scored = client.post("/api/score", data={"phrase_id": custom[0]["id"], "recognized": "أهلا بالبيت"})
    assert scored.status_code == 200
    vocabulary = client.post("/admin/vocabulary", data={"english": "project", "spanish": "proyecto", "spanish_pronunciation": "proh-YEHK-toh", "arabic": "مشروع", "arabic_transliteration": "mashrūʿ", "category": "Work", "part_of_speech": "noun", "cognate": "1"})
    assert vocabulary.status_code == 302
    words = client.get("/api/catalog").get_json()["lexicon"]["vocabulary"]
    assert any(item["english"] == "project" and item["custom"] for item in words)


def test_opi_estimate(client):
    response = client.post("/api/opi-score", data={"language": "spanish", "recognized": "Necesito cambiar la cita porque mi hija está enferma y no puede venir hoy"})
    assert response.status_code == 200
    assert response.get_json()["practice_level"] in {"1", "1+", "2"}


def test_scoring_helpers():
    assert score_words("¿Dónde estás?", "donde estas")["score"] == 100.0
    assert score_words("وينك؟", "وينه")["score"] == 75.0
    assert cipher_for("kee-SYEH-rah pro-grah-MAR") == "k·S·r p·g·M"
    assert measured_wpm("uno dos tres cuatro", 2.0)["wpm"] == 120
    assert measured_wpm("وينك", 1.0)["wpm"] is None
