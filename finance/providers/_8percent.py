import json
import pickle

from logbook import Logger
import requests

from finance.providers import Provider
from finance.utils import extract_numbers, parse_date


LOGIN_URL = 'https://8percent.kr/user/login/'
DATE_FORMAT = '%y.%m.%d'

log = Logger(__name__)


class _8Percent(Provider):
    session = None

    def login(self, username, password):
        """Returns a cookie string if login is successful."""
        self.session = session = requests.session()

        session.get(LOGIN_URL)
        csrf_token = session.cookies['csrftoken']

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
        cookies = session.cookies
        cookies = {k: v for k, v in zip(cookies.keys(), cookies.values())}

        resp = session.post(LOGIN_URL, headers=headers, data=data,
                            cookies=cookies)
        self.store_session(session)
        return resp

    def get_cookies(self, url):
        resp = requests.get(url)
        cookies = resp.cookies
        return {k: v for k, v in zip(cookies.keys(), cookies.values())}

    def store_session(self, session):
        with open('/tmp/8percent.session', 'wb') as fout:
            pickle.dump(requests.utils.dict_from_cookiejar(session.cookies),
                        fout)

    def load_session(self):
        with open('/tmp/8percent.session', 'rb') as fin:
            cookies = requests.utils.cookiejar_from_dict(pickle.load(fin))
            self.session = requests.session()
            self.session.cookies = cookies
            return self.session

    def store_cookies(self, cookies):
        """Stores cookies in a JSON format.

        :type cookies: dict"""
        with open('/tmp/8percent-cookies.json', 'w') as fout:
            fout.write(json.dumps(cookies))

    def load_cookies(self):
        """Loads cookies stored in a JSON format."""
        with open('/tmp/8percent-cookies.json') as fin:
            return json.loads(fin.read())

    def fetch_data(self, bond_id):
        if self.session is None:
            self.load_session()

        url = 'https://8percent.kr/my/repayment_detail/{}/'.format(bond_id)
        log.info('Fetching bond information from {}', url)
        headers = {
            'Accept-Encoding': 'text/html',
            'Accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/webp,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/49.0.2623.87 Safari/537.36',
        }
        resp = self.session.get(url, headers=headers)
        return resp

    def parse_data(self, raw):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, 'html.parser')

        def extract_div_text(soup, id=None, class_=None):
            if id:
                try:
                    return soup.find('div', id=id).text.strip()
                except:
                    raise Exception(
                        '<div id="{}"> could not be found'.format(id))
            elif class_:
                try:
                    return soup.find('div', class_=class_).text.strip()
                except:
                    raise Exception(
                        '<div class="{}"> could not be found'.format(class_))
            else:
                return Exception('Either id or class must be provided')

        def etni(soup, id, f):
            return f(extract_numbers(extract_div_text(soup, id=id)))

        def etnc(soup, class_, f):
            return f(extract_numbers(extract_div_text(soup, class_=class_)))

        name = extract_div_text(soup, id='Text_298')
        started_at = parse_date(extract_div_text(soup, id='Text_250'),
                                DATE_FORMAT)
        grade = extract_div_text(soup, id='Text_264')
        duration = etni(soup, 'Text_278', int)
        apy = etni(soup, 'Text_218', float) / 100
        amount = etni(soup, 'Text_300', int)

        log.info('Parsed: {}, {}, {}, {}, {}, {}', name, started_at, grade,
                 duration, apy, amount)

        rows = soup.find_all('div', class_='Box_444')
        def gen_records(rows):
            for row in rows:
                date = parse_date(extract_div_text(row, class_='Cell_445'),
                                  DATE_FORMAT)
                principle = etnc(row, 'Cell_451', int)
                interest = etnc(row, 'Cell_448', int)
                tax = etnc(row, 'Cell_449', int)
                fees = etnc(row, 'Cell_452', int)
                returned = etnc(row, 'Cell_453', int)

                # Make sure the parsed data is correct
                try:
                    assert returned == principle + interest - (tax + fees)
                except AssertionError:
                    import pdb; pdb.set_trace()
                    pass

                yield date, principle, interest, tax, fees

        return {
            'name': name,
            'started_at': started_at,
            'grade': grade,
            'duration': duration,
            'annual_percentage_yield': apy,
            'amount': amount,
            'records': list(gen_records(rows)),
        }
