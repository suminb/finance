from bs4 import BeautifulSoup
import requests

from finance.ext.search.base import Listing


base_url = "https://finance.naver.com"


class PaginatedResult:
    def __init__(self, query, page):
        self.soup = None
        self.query = query
        self.page = page
        self.max_page = 0

    @property
    def has_next_page(self):
        return self.page < self.max_page

    def fetch(self):
        # TODO: User-Agent and other headers
        resp = requests.get(
            f"{base_url}/search/searchList.nhn",
            params={"query": self.query.encode("euc-kr"), "page": self.page},
        )
        self.soup = BeautifulSoup(resp.text, features="lxml")

        self.max_page = max(int(p.text) for p in self.soup.select("div.paging a"))

        for table_row in self.soup.select("table.tbl_search tbody tr"):
            table_cols = table_row.select("td")
            anchor = table_row.find("a")
            price_col = table_cols[1]
            volume_col = table_cols[6]

            url = base_url + anchor.attrs["href"]
            symbol = url[-6:]
            name = anchor.text
            price = int(price_col.text.replace(",", ""))
            volume = int(volume_col.text.replace(",", ""))

            yield Listing(symbol, name, url, price, volume)


class NaverSearch:
    def search(self, query):
        """Searches for listings that match the given query. This returns a
        list of triples of (symbol, name, url).
        """
        page = 1
        while True:
            result_page = PaginatedResult(query, page)
            for row in result_page.fetch():
                yield row

            if result_page.has_next_page:
                page += 1
            else:
                break


def search_naver_listings(query: str):
    return NaverSearch().search(query)
