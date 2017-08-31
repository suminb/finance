Personal Finance Project
========================

.. image:: https://travis-ci.org/suminb/finance.svg?branch=develop
   :target: https://travis-ci.org/suminb/finance

.. image:: https://coveralls.io/repos/github/suminb/finance/badge.svg?branch=develop
   :target: https://coveralls.io/github/suminb/finance?branch=develop

NOTE: 제가 주로 사용하는 에디터인 vim 에서 한글 타이핑이 불편하기 때문에 영어로
문서를 작성하는 것이 일반적이지만, 이 프로젝트의 경우 한국어를 사용하는 청중이
대부분인 관계로 문서를 한국어로 작성합니다.


목표
----
이 프로젝트의 목적은 크게 두 가지입니다.

#. 총 자산 가치를 자동으로 추적하고 (비공식) SB 펀드의 가격을 산정하기.
#. 장기 가치 투자에 필요한 보조 도구들을 제공하기.


비전
----
`NDC 2016 - 프로그래머가 투자하는 법 <http://www.slideshare.net/suminb/how-programmers-invest>`_


현재 상태
---------
코드를 보신 분은 아시겠지만, 이 프로젝트는 미완성 상태입니다. 아니, 그냥 미완성
상태가 아니라 시작한지 얼마 되지 않았다고 얘기 하는편이 더 정확하겠군요. 지금
구현된 기능은 다음과 같습니다.

* 데이터베이스 모델: 기본적인 틀은 갖추어졌지만, 아직 부족한 점이 많아 앞으로 점진적으로 개선해 나갈 계획입니다. 데이터베이스 마이그레이션 도구로는 `Alembic <https://pypi.python.org/pypi/Flask-Alembic>`_ 을 사용할 계획입니다.

* 금융 자산 가격 가져오기: 여러가지 데이터 소스로부터 금융 자산 가격 정보를 받아옵니다.

  * 주식: `야후 파이낸스 <http://finance.yahoo.com>`_ 에서 받아옵니다. 20분 지연된 정보이긴 하지만, 일 단위 가격을 받아오는 것이기 때문에 지연 시간은 중요하지 않습니다.
  * 펀드: 금융투자협회(KOFIA)에 공시된 정보를 받아옵니다.
  * 8퍼센트: API를 제공하지 않기 때문에 HTML을 파싱해서 정보를 가져옵니다.


Daily Net Asset Values
**********************

매일 총 자산 가치(net asset value; NAV)를 합산하여 그래프로 보여줍니다. 이는 펀드의 단위 가격을 산정하는데 필수적인 데이터입니다.

.. figure:: http://s33.postimg.org/duyhsnxrz/net_worth.png
    :align: center
    :alt: Daily net asset values


지금 고민중인 내용들
--------------------
* `수익률 계산 <https://github.com/suminb/finance/wiki/%EC%88%98%EC%9D%B5%EB%A5%A0-%EA%B3%84%EC%82%B0>`_
* `전자공시데이터(DART) 가져오기 <https://github.com/suminb/finance/issues/1>`_


앞으로 할 일들
--------------
* 웹 인터페이스: 포트폴리오 구성을 한 눈에 볼 수 있는 인터페이스를 만들 계획입니다. 처음 써보는 `Angular <https://angular.io/docs/ts/latest/>`_ 로 웹 인터페이스를 작성하는 중입니다.
* 자동으로 데이터 받아오기: 주식, 펀드 가격 등 거래소에 공시되는 가격을 주기적으로 받아오는 무언가를 만들어야 합니다. 사용할 도구로는 AWS Lambda가 적당해보입니다.

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
        -t postgres

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

