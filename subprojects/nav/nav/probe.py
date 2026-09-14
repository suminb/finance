"""Format discovery for 미래에셋 거래내역조회 (0650) exports.

This module reads the raw CSV with the standard library only. It deliberately
avoids finance.providers.miraeasset so that it still works when the export
does not match that parser's expectations -- finding out how the export is
actually shaped is the whole point.
"""

import codecs
import csv
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple

DEFAULT_ENCODING = "euc-kr"
CATEGORY_COLUMN = "거래종류"
NAME_COLUMN = "종목명"


@dataclass
class CategorySummary:
    category: str
    count: int
    sample: Dict[str, str]


def read_rows(path: str, encoding: str = DEFAULT_ENCODING) -> Tuple[List[str], List[List[str]]]:
    """Reads a 0650 export into a header list and a list of row lists."""
    with codecs.open(path, "r", encoding=encoding) as fin:
        reader = csv.reader(fin)
        headers = [h.strip() for h in next(reader)]
        rows = [[c.strip() for c in row] for row in reader if any(c.strip() for c in row)]
    return headers, rows


def summarize_categories(headers: List[str], rows: List[List[str]]) -> List[CategorySummary]:
    """Counts distinct 거래종류 values, keeping one sample row for each."""
    index = headers.index(CATEGORY_COLUMN)
    counts: Counter = Counter(row[index] for row in rows)
    samples: Dict[str, Dict[str, str]] = {}
    for row in rows:
        samples.setdefault(row[index], dict(zip(headers, row)))
    return [
        CategorySummary(category=category, count=count, sample=samples[category])
        for category, count in counts.most_common()
    ]


def _looks_numeric(value: str) -> bool:
    stripped = value.replace(",", "").replace("-", "").replace(".", "")
    return bool(stripped) and stripped.isdigit()


def format_report(headers: List[str], rows: List[List[str]]) -> str:
    """Renders everything Tasks 3 and 4 need in order to write the YAML files."""
    lines = [
        f"columns: {len(headers)}",
        f"rows: {len(rows)}",
        "",
        "== 거래종류 ==",
    ]
    for summary in summarize_categories(headers, rows):
        lines.append(f"  {summary.category}  x{summary.count}")
        for key in (NAME_COLUMN, "통화코드", "거래금액", "수량", "단가", "수수료", "제세금합"):
            if key in summary.sample:
                lines.append(f"      {key}: {summary.sample[key]!r}")

    comma_columns = sorted(
        {
            headers[i]
            for row in rows
            for i in range(len(row))
            if "," in row[i] and _looks_numeric(row[i])
        }
    )
    fractional_columns = sorted(
        {
            headers[i]
            for row in rows
            for i in range(len(row))
            if "." in row[i] and _looks_numeric(row[i])
        }
    )

    lines += ["", "== numeric formats =="]
    lines.append(
        "  thousands separators: " + (", ".join(comma_columns) if comma_columns else "(none)")
    )
    lines.append(
        "  fractional values: " + (", ".join(fractional_columns) if fractional_columns else "(none)")
    )

    if NAME_COLUMN in headers:
        name_index = headers.index(NAME_COLUMN)
        names = sorted({row[name_index] for row in rows if row[name_index]})
        lines += ["", "== 종목명 =="]
        lines += [f"  {name}" for name in names]

    return "\n".join(lines)
