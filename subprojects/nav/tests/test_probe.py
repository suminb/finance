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
