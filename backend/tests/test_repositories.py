from src.core.settings import SRC_DIR


# The service commits once, at the end of its flow: a repository that commits would save half of it
def test_no_repository_commits():
    repositories = list(SRC_DIR.glob("modules/*/repositories/*.py"))

    assert repositories and [file.name for file in repositories if "db.commit()" in file.read_text()] == []
