from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ce108.config import DB_PATH
from ce108.seed import seed_database
from ce108.services import create_beta_student


def main() -> None:
    parser = argparse.ArgumentParser(description='Create a CE108 external beta student account.')
    parser.add_argument('--email', required=True, help='Tester email address.')
    parser.add_argument('--password', required=True, help='Initial password. Use at least 8 characters.')
    parser.add_argument('--display-name', required=True, help='Display name shown in CE108.')
    parser.add_argument('--grade', default='4年')
    parser.add_argument('--school-name', default='CE108外部β')
    parser.add_argument('--target-exam-year', type=int)
    parser.add_argument('--db-path', default=str(DB_PATH))
    args = parser.parse_args()

    db_path = Path(args.db_path)
    seed_database(db_path)
    user = create_beta_student(
        args.email,
        args.password,
        args.display_name,
        args.grade,
        args.school_name,
        args.target_exam_year,
        db_path,
    )
    print('Created CE108 beta student account.')
    print(f"  id: {user['id']}")
    print(f"  email: {user['email']}")
    print(f"  display_name: {user['display_name']}")
    print('  password: value provided by --password')


if __name__ == '__main__':
    main()
