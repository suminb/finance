import requests

from finance.providers import Provider


LOGIN_URL = 'https://8percent.kr/user/login/'


class _8Percent(Provider):
    def login(self, username, password):
        """Returns a cookie string if login is successful."""
        client = requests.session()

        client.get(LOGIN_URL)
        csrf_token = client.cookies['csrftoken']

        headers = {
            'Origin': 'https://8percent.kr',
            'Referer': LOGIN_URL,
        }
        data = {
            'csrfmiddlewaretoken': csrf_token,
            'type': 'login',
            'email': username,
            'password': password,
        }
        cookies = client.cookies
        cookies = {k: v for k, v in zip(cookies.keys(), cookies.values())}
        resp = client.post(LOGIN_URL, headers=headers, data=data,
                           cookies=cookies)
        return resp

    def get_cookies(self, url):
        resp = requests.get(url)
        cookies = resp.cookies
        return {k: v for k, v in zip(cookies.keys(), cookies.values())}

    def get_csrf_token(self, url):
        resp = requests.get(url)
        return resp.cookies['csrftoken']
