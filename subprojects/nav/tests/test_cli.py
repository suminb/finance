from click.testing import CliRunner

from nav.cli import cli


def test_rebuild_checks_for_exports_before_deleting_data(tmp_path):
    """A rebuild that cannot proceed must not have already destroyed data/.

    Both data/ and imports/ are gitignored, so once data/ is gone the only
    way back is the user's original broker exports. If imports/ turns out
    to be empty (wrong --root, nothing there yet, a misnamed file), the
    precondition failure must be reported before any deletion happens.
    """
    root = tmp_path
    data_dir = root / "data"
    data_dir.mkdir()
    marker = data_dir / "transaction.parquet"
    marker.write_bytes(b"not really a parquet file, just a marker")
    (root / "imports").mkdir()  # present but empty: no *.csv to rebuild from

    runner = CliRunner()
    result = runner.invoke(cli, ["rebuild", "--root", str(root), "--yes"])

    assert result.exit_code != 0
    assert data_dir.exists()
    assert marker.exists()
