from datetime import datetime
import pytz

import pytest

from finance.ext.warehouse import make_combination_indices


@pytest.mark.parametrize(
    ["indices", "static_indices", "r", "expected"],
    [
        ([1, 2, 3, 4], [], 1, [[1], [2], [3], [4]]),
        ([1, 2, 3], [], 2, [[1, 2], [1, 3], [2, 3]]),
        ([5, 4, 3], [], 3, [[5, 4, 3]]),
        (
            "abcd",
            [],
            2,
            [["a", "b"], ["a", "c"], ["a", "d"], ["b", "c"], ["b", "d"], ["c", "d"]],
        ),
        ([1, 2, 3, 4], [1], 2, [[1, 2], [1, 3], [1, 4]]),
        ([1, 2, 3, 4], [2, 3], 3, [[2, 3, 1], [2, 3, 4]]),
    ],
)
def test_make_combination_indices(indices, static_indices, r, expected):
    assert list(make_combination_indices(indices, static_indices, r, 1))[0] == expected


def parse_dt(str_dt, tz=pytz.timezone("America/New_York")):
    return datetime.strptime(str_dt + " 00:00:00", "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=tz
    )
