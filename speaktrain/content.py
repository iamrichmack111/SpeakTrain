import json
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"


def merge_nested(target, updates):
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_nested(target[key], value)
        else:
            target[key] = value


@lru_cache(maxsize=1)
def lessons():
    with (DATA_DIR / "lessons.json").open(encoding="utf-8") as handle:
        catalog = json.load(handle)
    with (DATA_DIR / "curriculum.json").open(encoding="utf-8") as handle:
        curriculum = json.load(handle)
    with (DATA_DIR / "lexicon.json").open(encoding="utf-8") as handle:
        lexicon = json.load(handle)
    catalog["courses"] = curriculum["courses"]
    catalog["bridges"] = curriculum["bridges"]
    catalog["lexicon"] = lexicon
    for language in catalog["languages"]:
        for scenario in language["scenarios"]:
            scenario.setdefault("course", "foundations" if scenario["id"] == "household" else "connection")
            scenario.setdefault("objective", f"Practice useful {scenario['name'].lower()} phrases.")
        new_scenarios = curriculum["scenarios"].get(language["id"], [])
        for scenario in new_scenarios:
            for phrase in scenario["phrases"]:
                if not phrase.get("registers"):
                    neutral = {"target": phrase["target"], "transliteration": phrase["transliteration"], "note": f"{phrase['note']} This wording is register-neutral."}
                    phrase["registers"] = {"informal": dict(neutral), "formal": dict(neutral)}
        language["scenarios"].extend(new_scenarios)
    with (DATA_DIR / "form_overrides.json").open(encoding="utf-8") as handle:
        overrides = json.load(handle)
    for language in catalog["languages"]:
        for scenario in language["scenarios"]:
            for phrase in scenario["phrases"]:
                if phrase["id"] in overrides:
                    merge_nested(phrase, overrides[phrase["id"]])
    return catalog


def all_phrases():
    for language in lessons()["languages"]:
        for scenario in language["scenarios"]:
            for phrase in scenario["phrases"]:
                yield language, scenario, phrase


def find_phrase(phrase_id):
    for language, scenario, phrase in all_phrases():
        if phrase["id"] == phrase_id:
            return language, scenario, phrase
    return None


def phrase_form(phrase, variant=None, register=None):
    form = {**phrase}
    selected_register = (phrase.get("registers") or {}).get(register or "")
    if selected_register:
        form.update(selected_register)
        form["selected_register"] = register
    selected_variant = ((selected_register or {}).get("variants") or {}).get(variant or "")
    if not selected_variant:
        selected_variant = (phrase.get("variants") or {}).get(variant or "")
    if selected_variant:
        form.update(selected_variant)
        form["selected_variant"] = variant
    return form


def courses():
    return lessons().get("courses", [])


def bridges():
    return lessons().get("bridges", [])


def find_bridge(bridge_id):
    return next((item for item in bridges() if item["id"] == bridge_id), None)


def public_catalog():
    return lessons()
