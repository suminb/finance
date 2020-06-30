from finance.ext.search.naver_finance import search_naver_listings


def search_listings(provider: str, query: str):
    """Searches for listings.

    Usage:

        >>> results = search_listings("naver", "KODEX")
        >>> next(results)
        Listing(069500, KODEX 200, https://finance.naver.com/item/main.nhn?code=069500)
        >>> next(results)
        Listing(091160, KODEX 반도체, https://finance.naver.com/item/main.nhn?code=091160)
        >>> next(results)
        Listing(091170, KODEX 은행, https://finance.naver.com/item/main.nhn?code=091170)
        >>> # Or, we could make it as a list
        >>> listings = list(results)
    """
    if provider == "naver":
        return search_naver_listings(query)
    else:
        raise ValueError(f"Invalid listing provider: {provider}")
