from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ce108.config import DB_PATH
from ce108.seed import seed_database
from ce108.services import upsert_past_exam_theme_ref


COLUMNS = [
    'exam_round',
    'exam_year',
    'session',
    'question_number',
    'topic_code',
    'derived_theme',
    'keywords',
    'source_url',
    'linked_question_id',
    'note',
]


def split_keywords(raw: str) -> list[str]:
    return [part.strip() for part in (raw or '').replace('、', ',').split(',') if part.strip()]


def row_is_incomplete(row: dict[str, str]) -> bool:
    required = ('exam_round', 'exam_year', 'session', 'question_number', 'topic_code', 'derived_theme')
    return any(not (row.get(key) or '').strip() for key in required)


def import_refs(input_path: Path, db_path: Path | str = DB_PATH, skip_incomplete: bool = True) -> int:
    seed_database(db_path)
    count = 0
    with input_path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        missing = [column for column in COLUMNS[:6] if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSVの必須列が不足しています: {', '.join(missing)}")
        for row in reader:
            if skip_incomplete and row_is_incomplete(row):
                continue
            linked_question_id = row.get('linked_question_id') or None
            upsert_past_exam_theme_ref(
                int(row['exam_round']),
                int(row['exam_year']),
                row['session'].strip(),
                int(row['question_number']),
                row['topic_code'].strip(),
                row['derived_theme'].strip(),
                split_keywords(row.get('keywords', '')),
                row.get('source_url') or None,
                int(linked_question_id) if linked_question_id else None,
                row.get('note', ''),
                db_path,
            )
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description='Import metadata-only past-exam theme references.')
    parser.add_argument('input', help='CSV path with past-exam theme metadata.')
    parser.add_argument('--db-path', default=str(DB_PATH))
    parser.add_argument('--strict', action='store_true', help='Fail instead of skipping incomplete template rows.')
    args = parser.parse_args()
    count = import_refs(Path(args.input), Path(args.db_path), skip_incomplete=not args.strict)
    print(f'Imported {count} past-exam theme refs')


if __name__ == '__main__':
    main()
