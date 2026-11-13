import os, sys, shutil, pytest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))


@pytest.fixture
def repo_copy(tmp_path):
    """A throw-away copy of the data part of the repo, so tests can run the builder safely."""
    dst = tmp_path / "repo"
    dst.mkdir()
    for d in ("sources", "days", "days-ml", "data", "reports"):
        if os.path.isdir(os.path.join(ROOT, d)):
            shutil.copytree(os.path.join(ROOT, d), dst / d)
    shutil.copy(os.path.join(ROOT, "index.json"), dst / "index.json")
    return str(dst)
