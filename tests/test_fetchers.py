from datetime import datetime, timedelta

import pytest

from finance.fetchers import fetch_stock_values


# Temporarily skip this test, as it appears the data format has been changed
@pytest.mark.skip
def test_fetch_stock_values():
    now = datetime.utcnow()
    start_date = now - timedelta(days=2)
    end_date = now - timedelta(days=1)
    rows = fetch_stock_values('SPY', start_date, end_date)

    for date, open_, high, low, close_, volume, provider in rows:
        assert isinstance(date, datetime)
        assert isinstance(open_, float)
        assert isinstance(high, float)
        assert isinstance(low, float)
        assert isinstance(close_, float)
        assert isinstance(volume, int)
        assert low <= open_ <= high
        assert low <= close_ <= high
        assert volume >= 0
        assert provider == 'yahoo'
