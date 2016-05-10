from bs4 import BeautifulSoup
import requests

from finance.providers import Provider


LOGIN_URL = 'https://8percent.kr/user/login'


class _8Percent(Provider):
    def login(self, username, password):
        """Returns a cookie string if login is successful."""
        csrf_token = self.get_csrf_token(LOGIN_URL)

        data = {
            'csrfmiddlewaretoken': csrf_token,
            'email': username,
            'password': password,
        }
        resp = requests.post(LOGIN_URL, data=data)
        import pdb; pdb.set_trace()
        pass

    def get_csrf_token(self, url):
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        return csrf_input['value']
