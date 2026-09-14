import json
from datetime import datetime, timezone

import pandas as pd

from nav import display, report, valuation


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


FRAME = pd.DataFrame(
    [
        {"date": utc(1), "nav_krw": 1000.0, "nav_usd": 1.0, "holdings_krw": 900.0,
         "cash_krw": 100.0, "cash_usd": 0.0, "fx_usdkrw": 1000.0, "stale": ""},
        {"date": utc(2), "nav_krw": 1100.0, "nav_usd": 1.1, "holdings_krw": 1000.0,
         "cash_krw": 100.0, "cash_usd": 0.0, "fx_usdkrw": 1000.0, "stale": "AAPL"},
    ],
    columns=valuation.COLUMNS,
)

HOLDINGS = [
    {"ticker": "AAPL", "quantity": 10.0, "price_krw": 100.0, "value_krw": 1000.0,
     "is_cash": False, "weight": 0.909},
    {"ticker": "_KRW", "quantity": 100.0, "price_krw": 1.0, "value_krw": 100.0,
     "is_cash": True, "weight": 0.091},
]


def payload():
    return report.build_payload(FRAME, HOLDINGS, display.summarize(FRAME))


def test_payload_series_is_json_serializable():
    json.dumps(payload())


def test_payload_dates_are_iso_strings():
    assert payload()["series"][0]["date"] == "2026-09-01"


def test_payload_carries_both_currencies():
    latest = payload()["summary"]
    assert latest["nav_krw"] == 1100.0
    assert latest["nav_usd"] == 1.1


def test_payload_carries_holdings_and_stale():
    p = payload()
    assert p["holdings"][0]["ticker"] == "AAPL"
    assert p["summary"]["stale"] == ["AAPL"]


def test_html_inlines_the_payload():
    html = report.render_html(payload())
    assert '<script type="application/json" id="nav-data">' in html
    assert '"nav_krw": 1100.0' in html or '"nav_krw":1100.0' in html


def test_html_has_no_unsubstituted_placeholder():
    html = report.render_html(payload())
    assert "{{" not in html


def test_html_pins_an_exact_chart_library_version():
    html = report.render_html(payload())
    assert "cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js" in html


def test_html_does_not_fetch_a_sibling_data_file():
    assert "fetch(" not in report.render_html(payload())


def test_html_escapes_embedded_closing_script_tags():
    """A ticker (or stale entry) containing '</script>' must not break out of

    the inlined JSON block. json.dumps does not escape '/', so a naive
    substitution would let a malicious or merely unlucky 종목명 coming from
    user-edited symbols.yaml terminate the <script> early and corrupt the
    page. The payload must still parse back to the exact original value,
    and the page must contain exactly one nav-data script tag.
    """
    evil_ticker = "</script><script>alert(1)"
    holdings = [
        {"ticker": evil_ticker, "quantity": 1.0, "price_krw": 1.0, "value_krw": 1.0,
         "is_cash": False, "weight": 1.0},
    ]
    p = report.build_payload(FRAME, holdings, display.summarize(FRAME))
    p["summary"]["stale"] = [evil_ticker]

    html = report.render_html(p)

    assert html.count('<script type="application/json" id="nav-data">') == 1
    assert "</script><script>alert" not in html

    start = html.index('id="nav-data">') + len('id="nav-data">')
    end = html.index("</script>", start)
    embedded = json.loads(html[start:end])
    assert embedded["holdings"][0]["ticker"] == evil_ticker
    assert embedded["summary"]["stale"] == [evil_ticker]
