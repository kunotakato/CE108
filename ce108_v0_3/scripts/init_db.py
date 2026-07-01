from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ce108.seed import export_question_template,seed_database
if __name__=='__main__':
    seed_database();print('CE108 database initialized');print(export_question_template())
