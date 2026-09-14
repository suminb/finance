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
    assert html.count("<script") == 3  # nav-data, the Chart.js src tag, the app script

    start = html.index('id="nav-data">') + len('id="nav-data">')
    end = html.index("</script>", start)
    embedded = json.loads(html[start:end])
    assert embedded["holdings"][0]["ticker"] == evil_ticker
    assert embedded["summary"]["stale"] == [evil_ticker]


def test_html_escapes_a_double_escaped_script_state_bypass():
    """'</' alone is not the whole hazard: '<!--' followed by '<script' with

    no literal '</' anywhere drives the HTML tokenizer into the "script data
    double escaped" state, in which the *legitimate* closing '</script>' of
    the nav-data block only demotes the state instead of closing the
    element -- swallowing the Chart.js tag and the app script as inert text,
    with JSON.parse throwing and nothing rendering, silently. Escaping every
    '<' (not just '</') must foreclose this too.
    """
    evil_ticker = "ok<!--x<script>alert(1)"
    assert "</" not in evil_ticker  # the earlier, narrower defense would miss this
    holdings = [
        {"ticker": evil_ticker, "quantity": 1.0, "price_krw": 1.0, "value_krw": 1.0,
         "is_cash": False, "weight": 1.0},
    ]
    p = report.build_payload(FRAME, holdings, display.summarize(FRAME))
    p["summary"]["stale"] = [evil_ticker]

    html = report.render_html(p)

    assert html.count("<script") == 3
    assert html.count('<script type="application/json" id="nav-data">') == 1

    start = html.index('id="nav-data">') + len('id="nav-data">')
    end = html.index("</script>", start)
    embedded = json.loads(html[start:end])
    assert embedded["holdings"][0]["ticker"] == evil_ticker
    assert embedded["summary"]["stale"] == [evil_ticker]


def test_render_html_substitutes_chartjs_before_payload():
    """The two placeholder substitutions must not be chainable into each other:

    substituting __PAYLOAD__ first and __CHARTJS__ second would let a
    payload string that happens to spell '__CHARTJS__' get rewritten into
    the CDN URL by the second .replace(), corrupting the embedded JSON.
    """
    holdings = [
        {"ticker": "__CHARTJS__", "quantity": 1.0, "price_krw": 1.0, "value_krw": 1.0,
         "is_cash": False, "weight": 1.0},
    ]
    p = report.build_payload(FRAME, holdings, display.summarize(FRAME))

    html = report.render_html(p)

    assert html.count(report.CHART_JS) == 1  # only in the real <script src> tag

    start = html.index('id="nav-data">') + len('id="nav-data">')
    end = html.index("</script>", start)
    embedded = json.loads(html[start:end])
    assert embedded["holdings"][0]["ticker"] == "__CHARTJS__"
