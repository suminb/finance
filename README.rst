Personal Finance Project
========================

.. image:: https://travis-ci.org/suminb/finance.svg?branch=develop
   :target: https://travis-ci.org/suminb/finance

.. image:: https://coveralls.io/repos/github/suminb/finance/badge.svg?branch=develop
   :target: https://coveralls.io/github/suminb/finance?branch=develop

.. image:: https://sonarcloud.io/api/project_badges/measure?project=finance&metric=alert_status
   :target: https://sonarcloud.io/dashboard?id=finance

NOTE: 제가 주로 사용하는 에디터인 vim 에서 한글 타이핑이 불편하기 때문에 영어로
문서를 작성하는 것이 일반적이지만, 이 프로젝트의 경우 한국어를 사용하는 청중이
대부분인 관계로 문서를 한국어로 작성합니다.

.. figure:: https://github.com/suminb/finance/raw/develop/moving_average.png
    :align: center
    :alt: Moving Average

목표
----
이 프로젝트의 목적은 크게 네 가지입니다.

#. 거래 내역 관리, 포트폴리오 시각화 등 자산 현황 파악하기.
#. 종목 리서치에 필요한 기능 제공하기.
#. 미리 설정해놓은 조건을 만족할 경우 알람 보내기.
#. 자동으로 거래하기. (먼 미래의 이야기)


비전
----
`NDC 2016 - 프로그래머가 투자하는 법 <http://www.slideshare.net/suminb/how-programmers-invest>`_

현재 연구중인 주제
------------------
- Currency exchange rate tracking
- Asset rebalancing
- Dual models: Database, ``DataFrame``

잠시 뒤로 미루어둔 주제
-----------------------
- 총 자산 가치 추적
- 자산 가격 받아오기: 여러가지 데이터 소스로부터 금융 자산 가격 정보를
  받아옵니다.

  - 주식: `야후 파이낸스 <http://finance.yahoo.com>`_\ 에서 받아옵니다. 20분
    지연된 정보이긴 하지만, 일 단위 가격을 받아오는 것이기 때문에 지연 시간은
    중요하지 않습니다.
  - 펀드: 금융투자협회(KOFIA)에 공시된 정보를 받아옵니다.

- `수익률 계산 <https://github.com/suminb/finance/wiki/%EC%88%98%EC%9D%B5%EB%A5%A0-%EA%B3%84%EC%82%B0>`_
- `전자공시데이터(DART) 가져오기 <https://github.com/suminb/finance/issues/1>`_

앞으로 할 일, 하지 않을 일
--------------------------
- 자동으로 데이터 받아오기: 주식, 펀드 가격 등 거래소에 공시되는 가격을
  주기적으로 받아오는 무언가를 만들어야 합니다. 사용할 도구로는 AWS Lambda가
  적당해보입니다.
- 달력을 다루는 도구 제공: 업무일(business days)은 국가와 지역마다 다를 수
  있습니다. 시차도 존재합니다. 따라서 여러 지역 시장에 투자할 경우 날짜, 시간
  정보를 효율적으로 다룰 수 있어야 합니다.
- 웹 인터페이스는 당분간 만들지 않을 예정입니다. 그대신 `주피터 노트북
  <https://jupyter.org>`_\ 에서 쉽게 사용할 수 있는 함수들을 제공하는데 집중할
  예정입니다.

(TODO: 내용 계속 채워넣기)

Daily Net Asset Values
**********************

매일 총 자산 가치(net asset value; NAV)를 합산하여 그래프로 보여줍니다. 이는
펀드의 단위 가격을 산정하는데 필수적인 데이터입니다.

(TODO: Prepare an illustration)

자산이 한가지 화폐 단위로 표기되는 경우에는 큰 어려움이 없습니다. 만약, 한국
주식만 보유하고 있다면 보유 종목의 총 가치와 원화 잔고를 합친 값이 총 자산
가치가 됩니다.

만약 다양한 화폐 단위로 표기되는 자산을 보유하고 있다면 가치 척도의 기준이 되는
화폐\ [1]_\ 를 정하고 그 화폐 기준으로 가치를 표기합니다. 예를 들어서, 한국
주식과 미국 주식을 보유하고 있고, 기준 화폐가 미국 달러(USD)라면 한국 주식
가격을 USD로 변환해서 합산해야 합니다.

.. [1] 코드에서는 ``base asset`` 이라는 이름으로 부르고 있지만, 더 적당한 용어가
   있다면 그것으로 대체할 용의가 있습니다.

Usage
-----

(TODO: 사용법 계속 채워넣기)

Search For Listings On Naver Finance
************************************

.. code::

   >>> from finance.ext.search import search_listings
   >>> results = search_listings("naver", "KODEX")
   >>> next(results)
   Listing(069500, KODEX 200, https://finance.naver.com/item/main.nhn?code=069500)
   >>> next(results)
   Listing(091160, KODEX 반도체, https://finance.naver.com/item/main.nhn?code=091160)
   >>> next(results)
   Listing(091170, KODEX 은행, https://finance.naver.com/item/main.nhn?code=091170)
   >>> # Or, we could make it as a list
   >>> listings = list(results)

Fetch Company Profiles From Naver Finance
*****************************************

.. code::

   >>> from finance.ext.profile import fetch_profile
   >>> profile = fetch_profile("naver", "063170")
   >>> profile.name
   서울옥션
   >>> profile.current_price
   4300
   >>> profile.eps
   -494
   >>> profile.bps
   4290

Fetch Financial Statements From DART (전자공시)
*********************************************

.. code::

   from finance.ext.dart import FinancialStatementRequest

   fs = FinancialStatementRequest()
   statements = fs.fetch(
       "00788773", 2020, "11012", "OFS",
       categorization_level1_key="fs_name",
       categorization_level2_key="account_name")

   statements["포괄손익계산서"]["당기순이익"].amount

   balance_sheet = statements["재무상태표"]
   debt_ratio = balance_sheet["부채총계"].amount / balance_sheet["자본총계"].amount

.. code::

   from finance.ext.dart import get_listed_corporations, search_corporations

   get_listed_corporations()
   search_corporations("NAVER")

Some Technical Details
----------------------

Create Tables
*************

.. code::

   finance create_all

Insert Test Data
****************

.. code::

   finance insert_test_data

Import Stock Values
*******************

.. code::

   finance fetch_stock_values 009830.KS | finance import_stock_values 009830.KS

The ``fetch_stock_values`` command strictly fetches data from Google Finance
as CSV, and the ``import_stock_values`` imports the structured data into the
database.

PostgreSQL in Docker
********************

.. code::

    docker run -d \
        -p 5432:5432 -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=qwerasdf \
        -e POSTGRES_DB=finance \
        -v $HOME/postgres:/var/lib/postgresql/data \
        -t postgres:10

psycopg2 on Mac
***************

If you fail to build the ``psycopg2`` package on Mac OS X with an error
message saying the following,

.. code::

    ld: library not found for -lssl

You may want to build ``pscycopg2`` as follows:

.. code::

    env LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib" pip install psycopg2

That's assuming you have ``openssl`` installed in your system. If you are
using ``brew`` you may install ``openssl`` as following:

.. code::

    brew install openssl

SonarCloud with Travis CI
*************************

Set ``SONAR_TOKEN`` environment variable on Travis CI repository settings.
Refer `this document <https://docs.travis-ci.com/user/sonarcloud/>`_ for more
details. Then you will need to set up ``sonar-project.properties`` file as
described `here
<https://docs.sonarqube.org/display/SCAN/Analyzing+with+SonarQube+Scanner>`_.
