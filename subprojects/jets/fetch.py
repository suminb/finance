from datetime import datetime
import json
import random
import time
import sys

import requests
from requests.adapters import HTTPAdapter, Retry
from logbook import Logger, StreamHandler


StreamHandler(sys.stderr).push_application()
log = Logger("jets")

sess = requests.Session()
retries = Retry(total=3,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
sess.mount('https://', HTTPAdapter(max_retries=retries))


def fetch_raw_flights(flight_number: str, page: int, timestamp: int, token: str):
    """
    curl 'https://api.flightradar24.com/common/v1/flight/list.json?query=dl324&fetchBy=flight&page=2&pk=&limit=100&token=&timestamp=1665499500&olderThenFlightId=2dcd9db8' \
  -H 'authority: api.flightradar24.com' \
  -H 'accept: */*' \
  -H 'accept-language: en-US,en;q=0.9,ko;q=0.8' \
  -H 'origin: https://www.flightradar24.com' \
  -H 'referer: https://www.flightradar24.com/' \
  -H 'sec-ch-ua: "Google Chrome";v="103", "Chromium";v="103", "Not=A?Brand";v="24"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-site' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36' \
  --compressed
    """
    # TODO: Handle olderThenFlightId?
    url = f'https://api.flightradar24.com/common/v1/flight/list.json?query={flight_number}&fetchBy=flight&page={page}&pk=&limit=100&token={token}&timestamp={timestamp}&olderThenFlightId=2dcd9db8'
    headers = {
        "Authority": "api.flightradar24.com",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        "Origin": "https://www.flightradar24.com",
        "Referer": "https://www.flightradar24.com/",
        "sec-ch-ua": 'Google Chrome";v="103", "Chromium";v="103", "Not=A?Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "macOS",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    }
    log.info(f"Fetching flights for {flight_number}, page {page}...")
    resp = sess.get(url, headers=headers)
    try:
        return json.loads(resp.text)
    except Exception as e:
        log.error(e)
        log.error(resp.text)
        with open(f"logs/fetch_raw_flights-{flight_number}-{page}.log", "w") as fout:
            fout.write(str(resp.status_code))
            fout.write(resp.text)


def fetch_all_flights(flight_number: str, token: str):
    page = 1
    last_timestamp = int(datetime.utcnow().timestamp())
    more = True
    while more:
        result = fetch_raw_flights(flight_number, page, last_timestamp, token)
        yield result

        try:
            resp = result["result"]["response"]
            page += 1
            more = resp["page"]["more"]
            last_timestamp = resp["data"][-1]["time"]["scheduled"]["departure"]
            last_id = resp["data"][-1]["identification"]["id"]

            log.info(f"id={last_id}, timestamp={last_timestamp} ({datetime.fromtimestamp(last_timestamp)}), more={more}")

            # for flight in result["result"]["response"]["data"]:
            #     yield flight
        except:
            with open(f"logs/fetch_all_flights-{flight_number}-{page}.log", "w") as fout:
                fout.write(json.dumps(result))
            raise

        time.sleep(random.random() * 1.5 + 0.75)


def main():
    flight_number = sys.argv[1]
    token = sys.argv[2]
    for flight in fetch_all_flights(flight_number, token):
        print(json.dumps(flight, separators=(",", ":")))


if __name__ == "__main__":
    main()


"""
Schema:

- result
  - request
    - ['callback', 'device', 'fetchBy', 'filterBy', 'format', 'limit', 'olderThenFlightId', 'page', 'pk', 'query', 'timestamp', 'token']
  - response
    - item: {'current': 100, 'total': None, 'limit': 100}
    - page: {'current': 1, 'total': None, 'more': True}
    - timestamp: 1673183442
    - aircraftInfo: ?
    - aircraftImages: ?
    - data[]:
      - identification: {'id': '2dcbd60f', 'row': None, 'number': {'default': 'DL1374', 'alternative': None}, 'callsign': 'DAL1374', 'codeshare': None}
      - status: {'live': False, 'text': 'Unknown', 'icon': None, 'estimated': None, 'ambiguous': False, 'generic': {'status': {'text': 'unknown',   'type': 'arrival',   'color': 'gray',   'diverted': None},  'eventTime': {'utc': None, 'local': None}}}
      - aircraft: (a relatively big dict)
      - owner: {'name': 'Delta Air Lines', 'code': {'iata': 'DL', 'icao': 'DAL'}}
      - airline: (empty)
      - airport
        - origin
        - destination
      - time
        - scheduled
          - departure: 1665445312
          - arrival: None
        - real
        - estimated
        - other
- _api
"""

"""
Example of error response:

{'result': {'request': {'callback': None, 'device': None, 'fetchBy': 'flight', 'filterBy': None, 'format': 'json', 'limit': 100, 'olderThenFlightId': 768449976, 'page': 1, 'pk': '', 'query': 'DL237', 'timestamp': 1665499500, 'token': '...'}, 'response': {'data': None, 'aircraftInfo': None, 'aircraftImages': None}}, '_api': {'copyright': 'Copyright (c) 2014-2023 Flightradar24 AB. All rights reserved.', 'legalNotice': 'The contents of this file and all derived data are the property of Flightradar24 AB for use exclusively by its products and applications. Using, modifying or redistributing the data without the prior written permission of Flightradar24 AB is not allowed and may result in prosecutions.'}}
"""
