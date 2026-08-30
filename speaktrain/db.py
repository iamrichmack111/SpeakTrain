import sqlite3

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'student',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phrase_id TEXT NOT NULL,
  language TEXT NOT NULL,
  scenario TEXT NOT NULL,
  score REAL NOT NULL,
  recognized TEXT NOT NULL DEFAULT '',
  variant TEXT NOT NULL DEFAULT 'default',
  user_id INTEGER REFERENCES users(id),
  duration_seconds REAL,
  speech_seconds REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS vocabulary_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  phrase_id TEXT NOT NULL,
  language TEXT NOT NULL,
  mode TEXT NOT NULL,
  quiz_type TEXT NOT NULL DEFAULT 'phrase',
  correct INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS conjugation_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  language TEXT NOT NULL,
  verb_id TEXT NOT NULL,
  tense TEXT NOT NULL,
  person TEXT NOT NULL,
  correct INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS review_state (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  item_type TEXT NOT NULL,
  item_id TEXT NOT NULL,
  mastery INTEGER NOT NULL DEFAULT 0,
  interval_days REAL NOT NULL DEFAULT 0,
  next_review TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  attempts INTEGER NOT NULL DEFAULT 0,
  correct_streak INTEGER NOT NULL DEFAULT 0,
  last_score REAL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, item_type, item_id)
);
CREATE TABLE IF NOT EXISTS custom_phrases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  language TEXT NOT NULL,
  course TEXT NOT NULL DEFAULT 'foundations',
  scenario TEXT NOT NULL DEFAULT 'Custom lessons',
  english TEXT NOT NULL,
  target TEXT NOT NULL,
  transliteration TEXT NOT NULL,
  formal_target TEXT,
  formal_transliteration TEXT,
  male_target TEXT,
  male_transliteration TEXT,
  female_target TEXT,
  female_transliteration TEXT,
  response TEXT,
  response_english TEXT,
  response_transliteration TEXT,
  note TEXT NOT NULL DEFAULT '',
  created_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS custom_vocabulary (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  english TEXT NOT NULL,
  spanish TEXT NOT NULL,
  spanish_pronunciation TEXT NOT NULL DEFAULT '',
  arabic TEXT NOT NULL,
  arabic_transliteration TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'Custom',
  part_of_speech TEXT NOT NULL DEFAULT 'word',
  cognate INTEGER NOT NULL DEFAULT 0,
  note TEXT NOT NULL DEFAULT '',
  created_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        get_db().executescript(SCHEMA)
        columns = {row[1] for row in get_db().execute("PRAGMA table_info(attempts)")}
        if "variant" not in columns:
            get_db().execute("ALTER TABLE attempts ADD COLUMN variant TEXT NOT NULL DEFAULT 'default'")
        if "user_id" not in columns:
            get_db().execute("ALTER TABLE attempts ADD COLUMN user_id INTEGER REFERENCES users(id)")
        if "speech_seconds" not in columns:
            get_db().execute("ALTER TABLE attempts ADD COLUMN speech_seconds REAL")
        user_columns = {row[1] for row in get_db().execute("PRAGMA table_info(users)")}
        if "role" not in user_columns:
            get_db().execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
        vocab_columns = {row[1] for row in get_db().execute("PRAGMA table_info(vocabulary_attempts)")}
        if "quiz_type" not in vocab_columns:
            get_db().execute("ALTER TABLE vocabulary_attempts ADD COLUMN quiz_type TEXT NOT NULL DEFAULT 'phrase'")
        if not get_db().execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone():
            first_user = get_db().execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
            if first_user:
                get_db().execute("UPDATE users SET role = 'admin' WHERE id = ?", (first_user["id"],))
        get_db().commit()
    app.teardown_appcontext(close_db)
