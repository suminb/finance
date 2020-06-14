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

        for element in self.soup.select("td.tit a"):
            url = base_url + element.attrs["href"]
            symbol = url[-6:]
            name = element.text
            yield Listing(symbol, name, url)


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
