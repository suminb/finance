"""A python module to load Shinhan Card monthly statement (emailed one) from a
csv file."""

import csv
import sys
import re
from datetime import datetime

NUMBER_OF_COLUMNS = 5
DATE_COLUMN = 0
DESCRIPTION_COLUMN = 2
AMOUNT_COLUMN = 6


def parse_date(raw):
    if re.match(r'\d{2}\.\d{2}\.\d{2}', raw):
        return datetime.strptime(raw, '%y.%m.%d')
    else:
        return None


def parse_amount(raw):
    # FIXME: The following regex does not exactly represent formatted numbers
    if re.match(r'[0-9,]+', raw):
        return float(raw.replace(',', ''))


def parse_row(row):
    if len(row) < NUMBER_OF_COLUMNS:
        return None

    return [parse_date(row[DATE_COLUMN]),
            row[DESCRIPTION_COLUMN].strip(),
            parse_amount(row[AMOUNT_COLUMN])]


def load(fin):
    reader = csv.reader(fin)

    for row in reader:
        cols = parse_row(row)
        if cols[0] is not None:
            yield cols


def main():
    with sys.stdin as csvin:
        with sys.stdout as csvout:
            writer = csv.writer(csvout)
            writer.writerow(['Date', 'Description', 'Amount'])

            for cols in load(csvin):
                cols[0] = cols[0].strftime('%m/%d/%Y')
                writer.writerow(cols)


if __name__ == '__main__':
    main()
