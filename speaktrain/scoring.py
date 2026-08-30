import re
import unicodedata


ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")


def normalize(text):
    text = unicodedata.normalize("NFKC", (text or "").lower())
    text = ARABIC_DIACRITICS.sub("", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"}))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", text, flags=re.UNICODE))


def word_distance(expected, actual):
    left, right = normalize(expected).split(), normalize(actual).split()
    rows, cols = len(left) + 1, len(right) + 1
    matrix = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        matrix[i][0] = i
    for j in range(cols):
        matrix[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            matrix[i][j] = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost)
    return matrix[-1][-1], max(1, len(left))


def character_score(expected, actual):
    left = normalize(expected).replace(" ", "")
    right = normalize(actual).replace(" ", "")
    rows, cols = len(left) + 1, len(right) + 1
    matrix = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        matrix[i][0] = i
    for j in range(cols):
        matrix[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            matrix[i][j] = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost)
    denominator = max(1, len(left), len(right))
    return max(0.0, round(100 * (1 - matrix[-1][-1] / denominator), 1))


def score_words(expected, actual):
    errors, total = word_distance(expected, actual)
    exact_word_score = max(0.0, round(100 * (1 - errors / total), 1))
    char_score = character_score(expected, actual)
    # One ASR letter should not erase all credit for a one- or two-word phrase.
    score = max(exact_word_score, char_score) if total <= 2 else exact_word_score
    expected_words = normalize(expected).split()
    actual_words = normalize(actual).split()
    missing = [word for word in expected_words if word not in actual_words]
    extra = [word for word in actual_words if word not in expected_words]
    return {
        "score": score,
        "word_score": exact_word_score,
        "character_score": char_score,
        "errors": errors,
        "total": total,
        "missing": missing,
        "extra": extra,
        "short_phrase_warning": total <= 2 and exact_word_score < char_score,
    }


def cipher_for(transliteration):
    tokens = transliteration.split()
    encoded = []
    for token in tokens:
        clean = re.sub(r"[^A-Za-zÀ-žʿʾ'-]", "", token)
        parts = [part for part in re.split(r"[-']+", clean) if part]
        initials = "·".join(part[0] for part in parts) if parts else token
        punctuation = "".join(ch for ch in token if ch in ",.?!;:")
        encoded.append(initials + punctuation)
    return " ".join(encoded)


def opi_estimate(transcript, duration=None):
    words = normalize(transcript).split()
    count = len(words)
    duration = float(duration or 0)
    wpm = round(count / duration * 60) if duration > 0 else None
    connectors = {"because", "although", "however", "pero", "porque", "aunque", "entonces", "لأن", "بس", "لكن", "بعدين"}
    connector_count = sum(1 for word in words if word in connectors)
    if count < 5:
        level = "0+"
    elif count < 15:
        level = "1"
    elif count < 35:
        level = "1+"
    elif connector_count or count >= 55:
        level = "2"
    else:
        level = "1+"
    return {
        "practice_level": level,
        "word_count": count,
        "wpm": wpm,
        "note": "Practice estimate only; an official OPI rating requires a certified rater and multiple tasks.",
    }


def measured_wpm(transcript, speech_seconds, minimum_words=3):
    words = len(normalize(transcript).split())
    if words < minimum_words or not speech_seconds or speech_seconds <= 0:
        return {"wpm": None, "wpm_confidence": "insufficient", "spoken_words": words}
    return {"wpm": round(words / speech_seconds * 60), "wpm_confidence": "measured", "spoken_words": words}
