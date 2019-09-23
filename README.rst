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
이 프로젝트의 목적은 크게 두 가지입니다.

#. 총 자산 가치를 자동으로 추적하고 (비공식) SB 펀드의 가격을 산정하기.
#. 장기 가치 투자에 필요한 보조 도구들을 제공하기.


비전
----
`NDC 2016 - 프로그래머가 투자하는 법 <http://www.slideshare.net/suminb/how-programmers-invest>`_

현재 연구중인 주제
------------------
- Asset rebalancing

잠시 뒤로 미루어둔 주제
-----------------------
- Determining net asset values
- Fetching asset prices: 여러가지 데이터 소스로부터 금융 자산 가격 정보를 받아옵니다.

  - 주식: `야후 파이낸스 <http://finance.yahoo.com>`_\ 에서 받아옵니다. 20분 지연된 정보이긴 하지만, 일 단위 가격을 받아오는 것이기 때문에 지연 시간은 중요하지 않습니다.
  - 펀드: 금융투자협회(KOFIA)에 공시된 정보를 받아옵니다.

- `수익률 계산 <https://github.com/suminb/finance/wiki/%EC%88%98%EC%9D%B5%EB%A5%A0-%EA%B3%84%EC%82%B0>`_
- `전자공시데이터(DART) 가져오기 <https://github.com/suminb/finance/issues/1>`_

Daily Net Asset Values
**********************

매일 총 자산 가치(net asset value; NAV)를 합산하여 그래프로 보여줍니다. 이는
펀드의 단위 가격을 산정하는데 필수적인 데이터입니다.

(TODO: Prepare an illustration)


앞으로 할 일들
--------------
- 웹 인터페이스: 포트폴리오 구성을 한 눈에 볼 수 있는 인터페이스를 만들 계획입니다. 처음 써보는 `Angular <https://angular.io/docs/ts/latest/>`_ 로 웹 인터페이스를 작성하는 중입니다.
- 자동으로 데이터 받아오기: 주식, 펀드 가격 등 거래소에 공시되는 가격을 주기적으로 받아오는 무언가를 만들어야 합니다. 사용할 도구로는 AWS Lambda가 적당해보입니다.

(TODO: 내용 계속 채워넣기)

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
