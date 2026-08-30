#!/usr/bin/env python3
"""Create the isolated Playwright database with admin/admin credentials."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from werkzeug.security import generate_password_hash

from speaktrain import create_app
from speaktrain.db import get_db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="instance/playwright.sqlite3")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    database = Path(args.database).resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    if args.fresh and database.exists():
        database.unlink()
    app = create_app({"DATABASE": str(database), "TESTING": True})
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO users (id, username, password_hash, role) VALUES (1, 'admin', ?, 'admin')",
            (generate_password_hash("admin"),),
        )
        db.commit()
    print(f"Seeded {database} with Playwright account admin/admin")


if __name__ == "__main__":
    main()
