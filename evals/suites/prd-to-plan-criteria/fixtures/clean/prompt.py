import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from brief import compose


def prompt(skill_dir, repo):
    return compose(skill_dir, repo)
