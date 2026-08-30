import csv
import copy
import io
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, g, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.security import generate_password_hash

from .auth import admin_required, login_required
from .content import all_phrases, bridges, find_bridge, find_phrase, phrase_form, public_catalog
from .db import get_db
from .scoring import cipher_for, measured_wpm, normalize, opi_estimate, score_words
from .speech import capability_status, generate_piper_audio, transcribe


bp = Blueprint("main", __name__)
LEVEL_NAMES = {1: "Phrase Scout", 2: "Routine Speaker", 3: "Conversation Builder", 4: "Narrator", 5: "OPI Challenger"}


@bp.get("/healthz")
def healthz():
    get_db().execute("SELECT 1").fetchone()
    return jsonify({"status": "ok", "service": "speaktrain"})


def profile_for(user_id):
    db = get_db()
    scores = [row[0] for row in db.execute("SELECT score FROM attempts WHERE user_id = ?", (user_id,)).fetchall()]
    vocab = [row[0] for row in db.execute("SELECT correct FROM vocabulary_attempts WHERE user_id = ?", (user_id,)).fetchall()]
    conjugations = [row[0] for row in db.execute("SELECT correct FROM conjugation_attempts WHERE user_id = ?", (user_id,)).fetchall()]
    xp = sum(max(1, round(score / 10)) for score in scores) + sum(10 if correct else 2 for correct in vocab + conjugations)
    level = xp // 100 + 1
    return {
        "xp": xp,
        "level": level,
        "title": LEVEL_NAMES.get(level, "Fluent Strategist"),
        "level_progress": xp % 100,
        "next_level_xp": 100 - (xp % 100),
        "vocabulary_correct": sum(vocab),
        "vocabulary_attempts": len(vocab),
        "conjugation_correct": sum(conjugations),
        "conjugation_attempts": len(conjugations),
    }


def custom_phrase(row):
    phrase = {
        "id": f"custom-{row['id']}", "english": row["english"], "target": row["target"],
        "transliteration": row["transliteration"], "note": row["note"],
        "response": row["response"], "responseEnglish": row["response_english"],
        "responseTransliteration": row["response_transliteration"], "custom": True,
    }
    if row["formal_target"]:
        phrase["registers"] = {
            "informal": {"target": row["target"], "transliteration": row["transliteration"]},
            "formal": {"target": row["formal_target"], "transliteration": row["formal_transliteration"] or row["transliteration"]},
        }
    variants = {}
    if row["male_target"]:
        variants["male"] = {"target": row["male_target"], "transliteration": row["male_transliteration"] or row["transliteration"]}
    if row["female_target"]:
        variants["female"] = {"target": row["female_target"], "transliteration": row["female_transliteration"] or row["transliteration"]}
    if variants:
        phrase["variants"] = variants
    return phrase


def custom_phrase_rows():
    return get_db().execute("SELECT * FROM custom_phrases ORDER BY id").fetchall()


def find_any_phrase(phrase_id):
    found = find_phrase(phrase_id)
    if found:
        return found
    if phrase_id.startswith("custom-") and phrase_id[7:].isdigit():
        row = get_db().execute("SELECT * FROM custom_phrases WHERE id = ?", (int(phrase_id[7:]),)).fetchone()
        if row:
            language = next(item for item in public_catalog()["languages"] if item["id"] == row["language"])
            scenario = {"id": f"custom-{row['course']}", "name": row["scenario"], "course": row["course"]}
            return language, scenario, custom_phrase(row)
    return None


def all_available_phrases():
    yield from all_phrases()
    for row in custom_phrase_rows():
        language = next(item for item in public_catalog()["languages"] if item["id"] == row["language"])
        scenario = {"id": f"custom-{row['course']}", "name": row["scenario"], "course": row["course"]}
        yield language, scenario, custom_phrase(row)


def update_review(user_id, item_type, item_id, score):
    db = get_db()
    current = db.execute("SELECT * FROM review_state WHERE user_id = ? AND item_type = ? AND item_id = ?", (user_id, item_type, item_id)).fetchone()
    streak = (current["correct_streak"] if current else 0) + 1 if score >= 80 else 0
    previous = current["mastery"] if current else 0
    if score < 60:
        mastery, interval = max(0, previous - 1), 10 / 1440
    else:
        ceiling = 1 if score < 80 else 2 if score < 90 else 3 if score < 98 else 4
        mastery = min(ceiling, previous + 1)
        interval = {1: 1, 2: 3, 3: 7, 4: 14 if streak < 3 else 30}[mastery]
    next_review = (datetime.now(timezone.utc) + timedelta(days=interval)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        """INSERT INTO review_state (user_id,item_type,item_id,mastery,interval_days,next_review,attempts,correct_streak,last_score,updated_at)
           VALUES (?,?,?,?,?,?,1,?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(user_id,item_type,item_id) DO UPDATE SET mastery=excluded.mastery, interval_days=excluded.interval_days,
           next_review=excluded.next_review, attempts=review_state.attempts+1, correct_streak=excluded.correct_streak,
           last_score=excluded.last_score, updated_at=CURRENT_TIMESTAMP""",
        (user_id, item_type, item_id, mastery, interval, next_review, streak, score),
    )
    return {"mastery": mastery, "mastery_label": ["New", "Learning", "Familiar", "Strong", "Mastered"][mastery], "next_review": next_review}


@bp.get("/")
@login_required
def index():
    return render_template("index.html", profile=profile_for(g.user["id"]), user=g.user)


@bp.get("/api/catalog")
def catalog():
    data = copy.deepcopy(public_catalog())
    for row in custom_phrase_rows():
        language = next(item for item in data["languages"] if item["id"] == row["language"])
        scenario_id = f"custom-{row['course']}"
        scenario = next((item for item in language["scenarios"] if item["id"] == scenario_id), None)
        if not scenario:
            scenario = {"id": scenario_id, "name": row["scenario"], "course": row["course"], "objective": "Administrator-created practice material.", "opiPrompts": [], "phrases": []}
            language["scenarios"].append(scenario)
        scenario["phrases"].append(custom_phrase(row))
    for row in get_db().execute("SELECT * FROM custom_vocabulary ORDER BY id").fetchall():
        data["lexicon"]["vocabulary"].append({
            "id": f"custom-vocab-{row['id']}", "english": row["english"], "spanish": row["spanish"],
            "spanishPronunciation": row["spanish_pronunciation"], "arabic": row["arabic"],
            "arabicTransliteration": row["arabic_transliteration"], "category": row["category"],
            "partOfSpeech": row["part_of_speech"], "cognate": bool(row["cognate"]), "note": row["note"], "custom": True,
        })
    for language in data["languages"]:
        for scenario in language["scenarios"]:
            for phrase in scenario["phrases"]:
                phrase["cipher"] = cipher_for(phrase["transliteration"])
                for form in (phrase.get("variants") or {}).values():
                    form["cipher"] = cipher_for(form["transliteration"])
                for form in (phrase.get("registers") or {}).values():
                    form["cipher"] = cipher_for(form["transliteration"])
                    for gender_form in (form.get("variants") or {}).values():
                        gender_form["cipher"] = cipher_for(gender_form["transliteration"])
    return jsonify(data)


@bp.get("/api/status")
def status():
    return jsonify(capability_status())


@bp.get("/api/audio/<phrase_id>")
@login_required
def audio(phrase_id):
    found = find_any_phrase(phrase_id)
    if not found:
        abort(404)
    language, _scenario, phrase = found
    variant = request.args.get("variant", "default")
    variant = variant if variant in {"male", "female"} else "default"
    register = request.args.get("register", "informal")
    register = register if register in {"formal", "informal"} else "informal"
    form = phrase_form(phrase, variant, register)
    destination = Path(current_app.instance_path) / "audio" / f"{phrase_id}-{variant}-{register}.wav"
    if not destination.exists() and not generate_piper_audio(form["target"], language["id"], destination):
        return jsonify({"error": "Piper voice is not configured", "fallback": "browser"}), 404
    return send_file(destination, mimetype="audio/wav")


@bp.post("/api/score")
@login_required
def score():
    phrase_id = request.form.get("phrase_id", "")
    found = find_any_phrase(phrase_id)
    if not found:
        return jsonify({"error": "Unknown phrase"}), 404
    language, scenario, phrase = found
    variant = request.form.get("variant", "default")
    variant = variant if variant in {"male", "female"} else "default"
    register = request.form.get("register", "informal")
    register = register if register in {"formal", "informal"} else "informal"
    form = phrase_form(phrase, variant, register)
    recognized = request.form.get("recognized", "").strip()
    speech_seconds = None
    if not recognized and "audio" in request.files:
        try:
            transcription = transcribe(request.files["audio"], language["id"], form["target"])
            recognized = transcription["text"]
            speech_seconds = transcription["speech_seconds"]
        except RuntimeError as error:
            return jsonify({"error": str(error), "manual_entry": True}), 503
    result = score_words(form["target"], recognized)
    recording_duration = request.form.get("duration", type=float)
    result.update(measured_wpm(recognized, speech_seconds))
    result["recording_duration"] = round(recording_duration, 1) if recording_duration else None
    result["speech_seconds"] = round(speech_seconds, 1) if speech_seconds else None
    get_db().execute(
        "INSERT INTO attempts (phrase_id, language, scenario, score, recognized, variant, user_id, duration_seconds, speech_seconds) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (phrase_id, language["id"], scenario["id"], result["score"], recognized, variant, g.user["id"], recording_duration, speech_seconds),
    )
    result["review"] = update_review(g.user["id"], "phrase", phrase_id, result["score"])
    get_db().commit()
    result.update({"recognized": recognized, "expected": form["target"], "variant": variant, "register": register, "profile": profile_for(g.user["id"])})
    return jsonify(result)


@bp.post("/api/opi-score")
@login_required
def opi_score():
    recognized = request.form.get("recognized", "").strip()
    language = request.form.get("language", "spanish")
    speech_seconds = None
    if not recognized and "audio" in request.files:
        try:
            transcription = transcribe(request.files["audio"], language)
            recognized = transcription["text"]
            speech_seconds = transcription["speech_seconds"]
        except RuntimeError as error:
            return jsonify({"error": str(error), "manual_entry": True}), 503
    result = opi_estimate(recognized, speech_seconds)
    result["recognized"] = recognized
    result["timing"] = measured_wpm(recognized, speech_seconds, minimum_words=10)
    return jsonify(result)


@bp.get("/api/vocabulary/question")
@login_required
def vocabulary_question():
    language_id = request.args.get("language", "spanish")
    mode = request.args.get("mode", "english_to_target")
    if mode in {"english_to_spanish", "spanish_to_arabic", "arabic_to_spanish"}:
        items = bridges()
        answer_item = random.choice(items)
        distractors = random.sample([item for item in items if item["id"] != answer_item["id"]], 3)
        if mode == "english_to_spanish":
            prompt, answer, key, direction = answer_item["english"], answer_item["spanish"], "spanish", "ltr"
        elif mode == "spanish_to_arabic":
            prompt, answer, key, direction = answer_item["spanish"], answer_item["arabic"], "arabic", "rtl"
        else:
            prompt, answer, key, direction = answer_item["arabic"], answer_item["spanish"], "spanish", "rtl"
        choices = [item[key] for item in distractors] + [answer]
        random.shuffle(choices)
        return jsonify({"phrase_id": answer_item["id"], "language": "bridge", "mode": mode, "quiz_type": "bridge", "prompt": prompt, "choices": choices, "direction": direction, "transliteration": answer_item["arabicTransliteration"], "note": answer_item["note"]})
    candidates = [(language, phrase) for language, _scenario, phrase in all_available_phrases() if language["id"] == language_id]
    if len(candidates) < 4:
        return jsonify({"error": "Not enough vocabulary items"}), 400
    language, phrase = random.choice(candidates)
    distractors = random.sample([item[1] for item in candidates if item[1]["id"] != phrase["id"]], 3)
    if mode == "target_to_english":
        prompt, answer = phrase["target"], phrase["english"]
        choices = [item["english"] for item in distractors] + [answer]
        direction = language["direction"]
    else:
        mode = "english_to_target"
        prompt, answer = phrase["english"], phrase["target"]
        choices = [item["target"] for item in distractors] + [answer]
        direction = "ltr"
    random.shuffle(choices)
    return jsonify({"phrase_id": phrase["id"], "language": language_id, "mode": mode, "quiz_type": "phrase", "prompt": prompt, "choices": choices, "direction": direction, "transliteration": phrase.get("transliteration", "")})


@bp.post("/api/vocabulary/answer")
@login_required
def vocabulary_answer():
    payload = request.get_json(silent=True) or {}
    if payload.get("quiz_type") == "bridge":
        item = find_bridge(payload.get("phrase_id", ""))
        if not item:
            return jsonify({"error": "Unknown bridge item"}), 404
        mode = payload.get("mode", "english_to_spanish")
        correct_answer = item["spanish"] if mode in {"english_to_spanish", "arabic_to_spanish"} else item["arabic"]
        correct = normalize(payload.get("selected", "")) == normalize(correct_answer)
        get_db().execute(
            "INSERT INTO vocabulary_attempts (user_id, phrase_id, language, mode, quiz_type, correct) VALUES (?, ?, ?, ?, 'bridge', ?)",
            (g.user["id"], item["id"], "bridge", mode, int(correct)),
        )
        review = update_review(g.user["id"], "bridge", item["id"], 100 if correct else 30)
        get_db().commit()
        return jsonify({"correct": correct, "correct_answer": correct_answer, "transliteration": item["arabicTransliteration"], "note": item["note"], "review": review, "profile": profile_for(g.user["id"])})
    found = find_any_phrase(payload.get("phrase_id", ""))
    if not found:
        return jsonify({"error": "Unknown phrase"}), 404
    language, _scenario, phrase = found
    mode = payload.get("mode", "english_to_target")
    correct_answer = phrase["english"] if mode == "target_to_english" else phrase["target"]
    correct = normalize(payload.get("selected", "")) == normalize(correct_answer)
    get_db().execute(
        "INSERT INTO vocabulary_attempts (user_id, phrase_id, language, mode, quiz_type, correct) VALUES (?, ?, ?, ?, 'phrase', ?)",
        (g.user["id"], phrase["id"], language["id"], mode, int(correct)),
    )
    review = update_review(g.user["id"], "vocabulary", phrase["id"], 100 if correct else 30)
    get_db().commit()
    return jsonify({"correct": correct, "correct_answer": correct_answer, "review": review, "profile": profile_for(g.user["id"])})


def mastery_name(value):
    return ["New", "Learning", "Familiar", "Strong", "Mastered"][max(0, min(4, value))]


@bp.get("/api/today")
@login_required
def today():
    db = get_db()
    states = [dict(row) for row in db.execute("SELECT * FROM review_state WHERE user_id = ? ORDER BY next_review", (g.user["id"],)).fetchall()]
    due = [row for row in states if row["next_review"] <= datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")]
    tracked = {(row["item_type"], row["item_id"]) for row in states}
    items = []
    for row in due[:12]:
        label, detail = row["item_id"], row["item_type"].title()
        if row["item_type"] == "phrase":
            found = find_any_phrase(row["item_id"])
            if found:
                label, detail = found[2]["english"], found[0]["name"]
        items.append({"type": row["item_type"], "id": row["item_id"], "label": label, "detail": detail, "mastery": row["mastery"], "mastery_label": mastery_name(row["mastery"]), "due": True})
    if len(items) < 8:
        for language, scenario, phrase in all_available_phrases():
            if ("phrase", phrase["id"]) not in tracked:
                items.append({"type": "phrase", "id": phrase["id"], "label": phrase["english"], "detail": f"New · {language['name']}", "mastery": 0, "mastery_label": "New", "due": False})
            if len(items) >= 8:
                break
    mastery_counts = {str(level): 0 for level in range(5)}
    for row in states:
        mastery_counts[str(row["mastery"])] += 1
    reviewed_phrases = {row["item_id"]: row["mastery"] for row in states if row["item_type"] == "phrase"}
    course_stats = []
    for course in public_catalog()["courses"]:
        phrase_ids = [phrase["id"] for _language, scenario, phrase in all_available_phrases() if scenario.get("course") == course["id"]]
        strong = sum(reviewed_phrases.get(phrase_id, 0) >= 3 for phrase_id in phrase_ids)
        course_stats.append({"id": course["id"], "name": course["name"], "total": len(phrase_ids), "strong": strong, "percent": round(strong / len(phrase_ids) * 100) if phrase_ids else 0})
    return jsonify({"profile": profile_for(g.user["id"]), "due_count": len(due), "items": items, "mastery": mastery_counts, "courses": course_stats})


def conjugation_value(language, verb, tense, person):
    value = verb["conjugations"][tense][person]
    return {"target": value, "transliteration": value} if isinstance(value, str) else value


@bp.get("/api/conjugation/question")
@login_required
def conjugation_question():
    language_id = request.args.get("language", "spanish")
    if language_id not in {"spanish", "arabic"}:
        language_id = "spanish"
    builder = public_catalog()["lexicon"]["builders"][language_id]
    tense = request.args.get("tense", "present")
    tense = tense if tense in {"present", "past"} else "present"
    verb = random.choice(builder["verbs"])
    subject = random.choice(builder["subjects"])
    answer = conjugation_value(language_id, verb, tense, subject["person"])
    pool = []
    for candidate_verb in builder["verbs"]:
        for candidate_subject in builder["subjects"]:
            value = conjugation_value(language_id, candidate_verb, tense, candidate_subject["person"])["target"]
            if normalize(value) != normalize(answer["target"]) and value not in pool:
                pool.append(value)
    choices = random.sample(pool, 3) + [answer["target"]]
    random.shuffle(choices)
    return jsonify({"language": language_id, "verb_id": verb["id"], "verb": verb["infinitive"], "verb_english": verb["english"], "tense": tense, "person": subject["person"], "subject": subject["target"], "subject_english": subject["english"], "choices": choices, "direction": builder["direction"]})


@bp.post("/api/conjugation/answer")
@login_required
def conjugation_answer():
    payload = request.get_json(silent=True) or {}
    language_id = payload.get("language", "spanish")
    builder = public_catalog()["lexicon"]["builders"].get(language_id)
    if not builder:
        return jsonify({"error": "Unknown language"}), 400
    verb = next((item for item in builder["verbs"] if item["id"] == payload.get("verb_id")), None)
    if not verb or payload.get("tense") not in {"present", "past"} or payload.get("person") not in {item["person"] for item in builder["subjects"]}:
        return jsonify({"error": "Unknown conjugation"}), 404
    answer = conjugation_value(language_id, verb, payload["tense"], payload["person"])
    correct = normalize(payload.get("selected", "")) == normalize(answer["target"])
    get_db().execute("INSERT INTO conjugation_attempts (user_id,language,verb_id,tense,person,correct) VALUES (?,?,?,?,?,?)", (g.user["id"], language_id, verb["id"], payload["tense"], payload["person"], int(correct)))
    review_id = f"{language_id}:{verb['id']}:{payload['tense']}:{payload['person']}"
    review = update_review(g.user["id"], "conjugation", review_id, 100 if correct else 30)
    get_db().commit()
    return jsonify({"correct": correct, "correct_answer": answer["target"], "transliteration": answer["transliteration"], "review": review, "profile": profile_for(g.user["id"])})


@bp.get("/api/conversation/question")
@login_required
def conversation_question():
    language_id = request.args.get("language", "spanish")
    candidates = [(language, scenario, phrase) for language, scenario, phrase in all_available_phrases() if language["id"] == language_id and phrase.get("response")]
    if len(candidates) < 4:
        return jsonify({"error": "Not enough guided dialogues"}), 400
    language, scenario, phrase = random.choice(candidates)
    distractors = random.sample([item[2]["responseEnglish"] for item in candidates if item[2]["id"] != phrase["id"]], 3)
    choices = distractors + [phrase["responseEnglish"]]
    random.shuffle(choices)
    return jsonify({"phrase_id": phrase["id"], "language": language_id, "scenario": scenario["name"], "english": phrase["english"], "prompt": phrase["target"], "transliteration": phrase["transliteration"], "choices": choices, "direction": language["direction"]})


@bp.post("/api/conversation/answer")
@login_required
def conversation_answer():
    payload = request.get_json(silent=True) or {}
    found = find_any_phrase(payload.get("phrase_id", ""))
    if not found or not found[2].get("response"):
        return jsonify({"error": "Unknown dialogue"}), 404
    phrase = found[2]
    correct = normalize(payload.get("selected", "")) == normalize(phrase["responseEnglish"])
    review = update_review(g.user["id"], "conversation", phrase["id"], 100 if correct else 30)
    get_db().commit()
    return jsonify({"correct": correct, "correct_answer": phrase["responseEnglish"], "response": phrase["response"], "transliteration": phrase.get("responseTransliteration", ""), "review": review, "profile": profile_for(g.user["id"])})


@bp.get("/api/progress")
@login_required
def progress():
    rows = [dict(row) for row in get_db().execute("SELECT * FROM attempts WHERE user_id = ? ORDER BY id", (g.user["id"],)).fetchall()]
    vocab_rows = [dict(row) for row in get_db().execute("SELECT * FROM vocabulary_attempts WHERE user_id = ?", (g.user["id"],)).fetchall()]
    conjugation_rows = [dict(row) for row in get_db().execute("SELECT * FROM conjugation_attempts WHERE user_id = ?", (g.user["id"],)).fetchall()]
    if not rows:
        return jsonify({
            "summary": {"attempts": 0, "average": None, "best": None, "average_wpm": None, "measured_pace_attempts": 0},
            "hardest": [], "recent": [], "profile": profile_for(g.user["id"]),
            "vocabulary": {"attempts": len(vocab_rows), "correct": sum(row["correct"] for row in vocab_rows)},
            "conjugation": {"attempts": len(conjugation_rows), "correct": sum(row["correct"] for row in conjugation_rows)},
            "recommendations": ["Complete five recorded attempts to unlock personalized guidance."], "techniques": memory_techniques(),
        })
    wpms, phrase_stats = [], {}
    for row in rows:
        pace = measured_wpm(row["recognized"], row.get("speech_seconds"))
        row.update(pace)
        if row["wpm"]:
            wpms.append(row["wpm"])
        found = find_any_phrase(row["phrase_id"])
        phrase = found[2] if found else {"english": row["phrase_id"]}
        item = phrase_stats.setdefault(row["phrase_id"], {"phrase_id": row["phrase_id"], "english": phrase["english"], "language": row["language"], "scores": [], "wpms": []})
        item["scores"].append(row["score"])
        if row["wpm"]:
            item["wpms"].append(row["wpm"])
    hardest = [{
        "phrase_id": item["phrase_id"], "english": item["english"], "language": item["language"],
        "attempts": len(item["scores"]), "average": round(sum(item["scores"]) / len(item["scores"]), 1),
        "average_wpm": round(sum(item["wpms"]) / len(item["wpms"])) if item["wpms"] else None,
    } for item in phrase_stats.values()]
    average = round(sum(row["score"] for row in rows) / len(rows), 1)
    average_wpm = round(sum(wpms) / len(wpms)) if wpms else None
    return jsonify({
        "summary": {"attempts": len(rows), "average": average, "best": max(row["score"] for row in rows), "average_wpm": average_wpm, "measured_pace_attempts": len(wpms)},
        "hardest": sorted(hardest, key=lambda item: item["average"])[:5], "recent": list(reversed(rows[-10:])),
        "recommendations": recommendations(average, average_wpm, hardest, len(rows)), "techniques": memory_techniques(),
        "profile": profile_for(g.user["id"]),
        "vocabulary": {"attempts": len(vocab_rows), "correct": sum(row["correct"] for row in vocab_rows)},
        "conjugation": {"attempts": len(conjugation_rows), "correct": sum(row["correct"] for row in conjugation_rows)},
    })


def period_start(period):
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period)
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if days else None


def report_data(user_id, period):
    since = period_start(period)
    clause, params = (" AND created_at >= ?", (user_id, since)) if since else ("", (user_id,))
    attempts = [dict(row) for row in get_db().execute(f"SELECT * FROM attempts WHERE user_id = ?{clause} ORDER BY created_at DESC", params).fetchall()]
    vocab = [dict(row) for row in get_db().execute(f"SELECT * FROM vocabulary_attempts WHERE user_id = ?{clause} ORDER BY created_at DESC", params).fetchall()]
    all_user_attempts = [dict(row) for row in get_db().execute("SELECT * FROM attempts WHERE user_id = ?", (user_id,)).fetchall()]
    phrase_scores = {}
    for row in all_user_attempts:
        phrase_scores.setdefault(row["phrase_id"], []).append(row["score"])
    ranked = []
    for language, scenario, phrase in all_available_phrases():
        scores = phrase_scores.get(phrase["id"], [])
        ranked.append((sum(scores) / len(scores) if scores else -1, language, scenario, phrase))
    limit = {"daily": 10, "weekly": 25, "monthly": 50}.get(period, 25)
    study = []
    for average, language, scenario, phrase in sorted(ranked, key=lambda item: item[0])[:limit]:
        study.append({"language": language["name"], "course": scenario.get("course", "foundations"), "english": phrase["english"], "target": phrase["target"], "transliteration": phrase["transliteration"], "average": None if average < 0 else round(average, 1)})
    scores = [row["score"] for row in attempts]
    vocab_correct = sum(row["correct"] for row in vocab)
    strengths = []
    weaknesses = []
    if scores and sum(scores) / len(scores) >= 85:
        strengths.append("Strong phrase-recognition accuracy in this period.")
    if vocab and vocab_correct / len(vocab) >= .8:
        strengths.append("Strong vocabulary recall, including multilingual bridge work.")
    if not strengths:
        strengths.append("You are building a baseline; consistent attempts are your current strength.")
    if not scores or sum(scores) / len(scores) < 75:
        weaknesses.append("Phrase production needs slower shadowing and immediate repetition.")
    if not vocab or vocab_correct / len(vocab) < .75:
        weaknesses.append("Vocabulary recall needs spaced, bidirectional review.")
    tips = ["Practice the first five study-sheet items aloud three times, then recall them without text.", "Review missed vocabulary after 10 minutes and again the next day.", "Alternate informal conversation with formal professional forms."]
    return {
        "period": period, "attempts": attempts, "vocab": vocab, "study": study,
        "summary": {"attempts": len(attempts), "average": round(sum(scores) / len(scores), 1) if scores else None, "vocabulary_attempts": len(vocab), "vocabulary_accuracy": round(vocab_correct / len(vocab) * 100) if vocab else None},
        "strengths": strengths, "weaknesses": weaknesses, "tips": tips,
    }


@bp.get("/report/<period>")
@login_required
def personal_report(period):
    if period not in {"daily", "weekly", "monthly"}:
        abort(404)
    return render_template("report.html", report=report_data(g.user["id"], period), report_user=g.user, generated=datetime.now().strftime("%B %d, %Y at %I:%M %p"))


@bp.get("/admin")
@admin_required
def admin():
    users = [dict(row) for row in get_db().execute("SELECT id, username, role, created_at FROM users ORDER BY username").fetchall()]
    for user in users:
        user["profile"] = profile_for(user["id"])
        user["report"] = report_data(user["id"], "monthly")
    return render_template(
        "admin.html", users=users, courses=public_catalog()["courses"],
        custom_phrases=[dict(row) for row in custom_phrase_rows()],
        custom_vocabulary=[dict(row) for row in get_db().execute("SELECT * FROM custom_vocabulary ORDER BY id DESC").fetchall()],
    )


@bp.post("/admin/users")
@admin_required
def admin_add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "student")
    if len(username) < 2 or len(password) < 6 or role not in {"student", "admin"}:
        return "Username, password, or role is invalid.", 400
    try:
        get_db().execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, generate_password_hash(password), role))
        get_db().commit()
    except Exception:
        return "That username already exists.", 409
    return redirect(url_for("main.admin"))


@bp.post("/admin/users/<int:user_id>/password")
@admin_required
def admin_password(user_id):
    password = request.form.get("password", "")
    if len(password) < 6:
        return "Password must contain at least six characters.", 400
    get_db().execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), user_id))
    get_db().commit()
    return redirect(url_for("main.admin"))


@bp.post("/admin/users/<int:user_id>/delete")
@admin_required
def admin_delete_user(user_id):
    if user_id == g.user["id"]:
        return "You cannot delete the account you are currently using.", 400
    target = get_db().execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        abort(404)
    if target["role"] == "admin" and get_db().execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0] <= 1:
        return "The final administrator cannot be deleted.", 400
    get_db().execute("DELETE FROM vocabulary_attempts WHERE user_id = ?", (user_id,))
    get_db().execute("DELETE FROM attempts WHERE user_id = ?", (user_id,))
    get_db().execute("DELETE FROM users WHERE id = ?", (user_id,))
    get_db().commit()
    return redirect(url_for("main.admin"))


@bp.get("/admin/grades.csv")
@admin_required
def admin_grades_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["username", "role", "level", "xp", "phrase_attempts", "average_match", "vocabulary_attempts", "vocabulary_accuracy", "strengths", "weaknesses", "tips"])
    for user in get_db().execute("SELECT id, username, role FROM users ORDER BY username").fetchall():
        report = report_data(user["id"], "monthly")
        profile = profile_for(user["id"])
        writer.writerow([user["username"], user["role"], profile["level"], profile["xp"], report["summary"]["attempts"], report["summary"]["average"], report["summary"]["vocabulary_attempts"], report["summary"]["vocabulary_accuracy"], " | ".join(report["strengths"]), " | ".join(report["weaknesses"]), " | ".join(report["tips"])])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=speaktrain-grades.csv"})


@bp.post("/admin/phrases")
@admin_required
def admin_add_phrase():
    language = request.form.get("language", "")
    course = request.form.get("course", "")
    required = [request.form.get(name, "").strip() for name in ("english", "target", "transliteration")]
    valid_courses = {item["id"] for item in public_catalog()["courses"]}
    if language not in {"spanish", "arabic"} or course not in valid_courses or not all(required):
        return "Language, course, English, target text, and transliteration are required.", 400
    fields = ["scenario", "english", "target", "transliteration", "formal_target", "formal_transliteration", "male_target", "male_transliteration", "female_target", "female_transliteration", "response", "response_english", "response_transliteration", "note"]
    values = [request.form.get(name, "").strip() or None for name in fields]
    values[0] = values[0] or "Custom lessons"
    values[-1] = values[-1] or "Administrator-created lesson."
    get_db().execute(
        f"INSERT INTO custom_phrases (language,course,{','.join(fields)},created_by) VALUES ({','.join('?' for _ in range(len(fields)+3))})",
        [language, course, *values, g.user["id"]],
    )
    get_db().commit()
    return redirect(url_for("main.admin") + "#curriculum")


@bp.post("/admin/phrases/<int:item_id>/delete")
@admin_required
def admin_delete_phrase(item_id):
    get_db().execute("DELETE FROM custom_phrases WHERE id = ?", (item_id,))
    get_db().execute("DELETE FROM review_state WHERE item_id = ?", (f"custom-{item_id}",))
    get_db().commit()
    return redirect(url_for("main.admin") + "#curriculum")


@bp.post("/admin/vocabulary")
@admin_required
def admin_add_vocabulary():
    fields = ["english", "spanish", "spanish_pronunciation", "arabic", "arabic_transliteration", "category", "part_of_speech", "note"]
    values = [request.form.get(name, "").strip() for name in fields]
    if not all(values[:5]):
        return "English, Spanish, Spanish pronunciation, Arabic, and Arabic transliteration are required.", 400
    values[5] = values[5] or "Custom"
    values[6] = values[6] or "word"
    get_db().execute(
        f"INSERT INTO custom_vocabulary ({','.join(fields)},cognate,created_by) VALUES ({','.join('?' for _ in range(len(fields)+2))})",
        [*values, int(request.form.get("cognate") == "1"), g.user["id"]],
    )
    get_db().commit()
    return redirect(url_for("main.admin") + "#curriculum")


@bp.post("/admin/vocabulary/<int:item_id>/delete")
@admin_required
def admin_delete_vocabulary(item_id):
    get_db().execute("DELETE FROM custom_vocabulary WHERE id = ?", (item_id,))
    get_db().commit()
    return redirect(url_for("main.admin") + "#curriculum")


def recommendations(average, average_wpm, phrase_stats, attempts):
    advice = []
    if average < 75:
        advice.append("Slow down and shadow the reference twice before recording. Accuracy should rise before speed.")
    elif average < 90:
        advice.append("Use cipher fading on the lowest-scoring phrases until you can produce them without text.")
    else:
        advice.append("Your recognition accuracy is strong. Start answering from English prompts without viewing the target phrase.")
    if average_wpm is None:
        advice.append("Pace needs a phrase of at least three recognized words. One-word clips are intentionally excluded from WPM.")
    elif average_wpm < 80:
        advice.append("Build automaticity with three clean shadowing repetitions; aim first for 80–110 speech-active WPM.")
    elif average_wpm > 160 and average < 90:
        advice.append("Your pace is outrunning accuracy. Reduce speed by roughly 15% and exaggerate final consonants.")
    else:
        advice.append(f"Your speech-active pace averages {average_wpm} WPM; keep it while improving spontaneous recall.")
    if phrase_stats:
        weakest = min(phrase_stats, key=lambda item: item["average"])
        advice.append(f"Priority phrase: “{weakest['english']}” has your lowest average match.")
    if attempts < 10:
        advice.append("More attempts are needed for a stable trend; complete at least ten across two sessions.")
    return advice


def memory_techniques():
    return [
        {"name": "Cipher fading", "steps": "Full phrase → syllable initials → first cue only → no text."},
        {"name": "Listen–shadow–recall", "steps": "Listen once, speak with the voice, then reproduce it from memory."},
        {"name": "Spaced retrieval", "steps": "Recall after 10 minutes, 1 day, 3 days, 7 days, 14 days, and 30 days."},
        {"name": "Bidirectional recall", "steps": "Produce Arabic/Spanish from English, then explain the foreign phrase in English."},
        {"name": "Variable substitution", "steps": "Replace the person, place, object, day, or time while retaining the sentence structure."},
        {"name": "Interleaving", "steps": "Mix household, appointment, romantic, past-tense, and problem-solving prompts instead of drilling one block."},
    ]
