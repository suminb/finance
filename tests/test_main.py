def test_portfolios_nav(testapp, portfolio):
    resp = testapp.get("/portfolios/{}/nav".format(portfolio.id))
    assert resp.status_code == 200
