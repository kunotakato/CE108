from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ce108.config import DB_PATH
from ce108.seed import seed_database
from ce108.services import set_user_password


def main() -> None:
    parser = argparse.ArgumentParser(description='Set a CE108 user password.')
    parser.add_argument('--email', required=True)
    parser.add_argument('--password', help='Use at least 8 characters. If omitted, you will be prompted without echo.')
    parser.add_argument('--db-path', default=str(DB_PATH))
    args = parser.parse_args()
    password = args.password
    if password is None:
        password = getpass.getpass('New password: ')
        confirm = getpass.getpass('Confirm password: ')
        if password != confirm:
            raise SystemExit('Passwords do not match.')

    db_path = Path(args.db_path)
    seed_database(db_path)
    user = set_user_password(args.email, password, db_path)
    print('Updated CE108 user password.')
    print(f"  id: {user['id']}")
    print(f"  email: {user['email']}")
    print('  password: value provided securely')


if __name__ == '__main__':
    main()
