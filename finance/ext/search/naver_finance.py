from bs4 import BeautifulSoup
import requests

from finance.ext.search.base import Listing


class NaverSearch:
    def __init__(self):
        self.soup = None

    def search(self, query):
        """Searches for listings that match the given query. This returns a
        list of triples of (symbol, name, url).
        """
        base_url = "https://finance.naver.com"
        resp = requests.get(f"{base_url}/search/searchList.nhn", params={"query": query.encode("euc-kr")})
        self.soup = BeautifulSoup(resp.text, features="lxml")

        for element in self.soup.select("td.tit a"):
            url = base_url + element.attrs["href"]
            symbol = url[-6:]
            name = element.text
            # TODO: We could make a wrapper class
            yield Listing(symbol, name, url)