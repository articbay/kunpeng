from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTIVE_VERSIONS = (PROJECT_ROOT / "migrations" / "versions_v3").resolve()


def test_alembic_uses_only_the_v3_production_chain():
    config = Config(PROJECT_ROOT / "alembic.ini")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["d2f6a91c8e47"]
    assert script.get_revision("935ae1532222") is not None
    assert {Path(path).resolve() for path in script.version_locations} == {
        ACTIVE_VERSIONS
    }
    assert {
        Path(revision.path).parent.resolve() for revision in script.walk_revisions()
    } == {ACTIVE_VERSIONS}
