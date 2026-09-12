from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ce108.config import DB_PATH
from ce108.database import fetch_all
from ce108.first_paid_pack import FIRST_PAID_TESTER_PACK_POLICY, FIRST_PAID_TESTER_PACK_TEXTS
from ce108.seed import seed_database


def export_first_paid_pack(output: Path, db_path: Path | str = DB_PATH) -> Path:
    seed_database(db_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    placeholders = ','.join('?' for _ in FIRST_PAID_TESTER_PACK_TEXTS)
    rows = fetch_all(
        f"""SELECT q.id,q.question_type,q.question_text,q.explanation_standard,q.explanation_detailed,
        q.importance,q.frequency_score,q.source_type,q.status,t.code topic_code,t.name topic_name,s.code subject_code,s.name subject_name
        FROM questions q
        LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary'
        LEFT JOIN topics t ON t.id=m.topic_id
        LEFT JOIN subjects s ON s.id=t.subject_id
        WHERE q.question_text IN ({placeholders})
        ORDER BY CASE q.question_text {' '.join(f'WHEN ? THEN {i}' for i, _ in enumerate(FIRST_PAID_TESTER_PACK_TEXTS, 1))} ELSE 999 END""",
        [*FIRST_PAID_TESTER_PACK_TEXTS, *FIRST_PAID_TESTER_PACK_TEXTS],
        db_path,
    )
    columns = [
        'pack_name','pack_version','pack_order','id','subject_code','subject_name','topic_code','topic_name',
        'question_type','question_text','choices_json','correct_choices','explanation_standard','explanation_detailed',
        'importance','frequency_score','source_type','status',
        'primary_review','learner_comment','needs_fix','fix_comment',
    ]
    with output.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for index, row in enumerate(rows, 1):
            choices = [dict(c) for c in fetch_all(
                'SELECT choice_code,choice_text,is_correct,explanation FROM question_choices WHERE question_id=? ORDER BY display_order',
                (row['id'],),
                db_path,
            )]
            writer.writerow({
                'pack_name': FIRST_PAID_TESTER_PACK_POLICY['name'],
                'pack_version': FIRST_PAID_TESTER_PACK_POLICY['version'],
                'pack_order': index,
                **{key: row[key] for key in row.keys()},
                'choices_json': json.dumps(choices, ensure_ascii=False),
                'correct_choices': ','.join(c['choice_code'] for c in choices if c['is_correct']),
                'primary_review': '未確認',
                'learner_comment': '',
                'needs_fix': '',
                'fix_comment': '',
            })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description='Export the CE108 First Paid Tester Pack.')
    parser.add_argument('--output', default='data/first_paid_tester_pack.csv')
    parser.add_argument('--db-path', default=str(DB_PATH))
    args = parser.parse_args()
    path = export_first_paid_pack(Path(args.output), Path(args.db_path))
    print(path)


if __name__ == '__main__':
    main()
