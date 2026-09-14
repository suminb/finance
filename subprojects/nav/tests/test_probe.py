import pytest

from nav import probe

SAMPLE = "subprojects/nav/tests/samples/miraeasset_0650_sample.csv"


def test_read_rows_returns_25_columns():
    headers, rows = probe.read_rows(SAMPLE)
    assert len(headers) == 25
    assert headers[0] == "거래일자"
    assert len(rows) == 4
    assert all(len(r) == 25 for r in rows)


def test_read_rows_preserves_quoted_commas():
    _, rows = probe.read_rows(SAMPLE)
    assert rows[0][5] == "1,500.00"


def test_summarize_categories_counts_and_samples():
    headers, rows = probe.read_rows(SAMPLE)
    summaries = probe.summarize_categories(headers, rows)
    by_name = {s.category: s for s in summaries}
    assert by_name["현금매수"].count == 2
    assert by_name["배당금"].count == 1
    assert by_name["출금"].count == 1
    assert by_name["현금매수"].sample["종목명"] == "애플"


def test_summarize_categories_sorted_by_count_desc():
    headers, rows = probe.read_rows(SAMPLE)
    counts = [s.count for s in probe.summarize_categories(headers, rows)]
    assert counts == sorted(counts, reverse=True)


def test_format_report_flags_thousands_separators():
    headers, rows = probe.read_rows(SAMPLE)
    report = probe.format_report(headers, rows)
    assert "거래금액" in report
    assert "thousands separators" in report


def test_format_report_lists_distinct_symbol_names():
    headers, rows = probe.read_rows(SAMPLE)
    report = probe.format_report(headers, rows)
    assert "애플" in report
    assert "삼성전자보통주" in report


def test_read_rows_on_a_wrongly_encoded_file_says_so(tmp_path):
    """An Excel round-trip re-saves the euc-kr export as UTF-8; that must not

    surface as a bare UnicodeDecodeError traceback.
    """
    path = tmp_path / "utf8.csv"
    path.write_bytes(open(SAMPLE, "rb").read().decode("euc-kr").encode("utf-8"))

    with pytest.raises(probe.MalformedExportError) as excinfo:
        probe.read_rows(str(path))
    assert "not euc-kr-encoded" in str(excinfo.value)
    assert "--encoding utf-8" in str(excinfo.value)


def test_read_rows_on_an_empty_file_says_so(tmp_path):
    """`next(reader)` on an empty file used to raise a bare StopIteration."""
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="euc-kr")

    with pytest.raises(probe.MalformedExportError, match="is empty"):
        probe.read_rows(str(path))


def test_summarize_categories_without_the_category_column_says_so():
    """`headers.index(...)` used to raise `ValueError: '거래종류' is not in list`."""
    with pytest.raises(probe.MalformedExportError) as excinfo:
        probe.summarize_categories(["a", "b"], [["1", "2"]])
    assert "거래종류" in str(excinfo.value)
    assert "0650" in str(excinfo.value)


def test_format_report_without_the_category_column_says_so():
    with pytest.raises(probe.MalformedExportError):
        probe.format_report(["a", "b"], [["1", "2"]])
