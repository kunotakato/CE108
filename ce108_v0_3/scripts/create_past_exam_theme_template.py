from __future__ import annotations

import argparse
import csv
from pathlib import Path


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


def estimate_exam_year(exam_round: int, latest_round: int, latest_year: int) -> int:
    return latest_year - (latest_round - exam_round)


def create_template(
    output: Path,
    start_round: int = 30,
    end_round: int = 39,
    latest_round: int = 39,
    latest_year: int = 2026,
    questions_per_session: int = 90,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for exam_round in range(start_round, end_round + 1):
            exam_year = estimate_exam_year(exam_round, latest_round, latest_year)
            for session in ('午前', '午後'):
                for question_number in range(1, questions_per_session + 1):
                    writer.writerow({
                        'exam_round': exam_round,
                        'exam_year': exam_year,
                        'session': session,
                        'question_number': question_number,
                        'topic_code': '',
                        'derived_theme': '',
                        'keywords': '',
                        'source_url': '',
                        'linked_question_id': '',
                        'note': '公式本文・選択肢・解説文は保存しない',
                    })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description='Create a metadata-only past-exam theme CSV template.')
    parser.add_argument('--output', default='data/past_exam_theme_refs_template_10y.csv')
    parser.add_argument('--start-round', type=int, default=30)
    parser.add_argument('--end-round', type=int, default=39)
    parser.add_argument('--latest-round', type=int, default=39)
    parser.add_argument('--latest-year', type=int, default=2026)
    parser.add_argument('--questions-per-session', type=int, default=90)
    args = parser.parse_args()
    path = create_template(
        Path(args.output),
        args.start_round,
        args.end_round,
        args.latest_round,
        args.latest_year,
        args.questions_per_session,
    )
    print(path)


if __name__ == '__main__':
    main()
