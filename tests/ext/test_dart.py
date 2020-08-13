from finance.ext.dart import search_corporations


def test_search_corporations():
    results = search_corporations("씨젠")
    assert len(results) == 1

    corp = results[0]
    assert "씨젠" == corp.name
    assert "00788773" == corp.dart_code
    assert "096530" == corp.stock_code