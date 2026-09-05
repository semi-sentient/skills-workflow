import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from brief import compose
from phases import BANDS as PHASE


def prompt(skill_dir, repo):
    return compose(skill_dir, phase=PHASE["phase"], criteria=PHASE["criteria"],
                   manifest=PHASE["manifest"], pointers=PHASE["pointers"], repo=repo)
