import csv
from datetime import datetime
from glob import glob

import edgar


class EdgarIndexRow:
    def __init__(self, raw_columns):
        (
            self.cik,
            self.title,
            self.type,
            date,
            self.txt_path,
            self.html_path,
        ) = raw_columns
        self.date = datetime.strptime(date, "%Y-%m-%d")

    def __repr__(self):
        return f"{self.cik}, {self.title}, {self.type}, {self.date}, {self.txt_path}, {self.html_path}"


def download_indexes():
    edgar.download_index(
        "/tmp/edgar",
        2020,
        skip_all_present_except_last=False
    )


def search(predicate: callable):
    for filename in glob("/tmp/edgar/*.tsv"):
        with open(filename) as fin:
            rows = csv.reader(fin, delimiter="|")
            for row in rows:
                row = EdgarIndexRow(row)
                if predicate(row):
                    yield row


if __name__ == "__main__":
    for row in search(lambda row: row.type == "NPORT-P"):
        print(row)