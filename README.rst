Personal Finance Project
========================

.. image:: https://travis-ci.org/suminb/finance.svg?branch=develop
   :target: https://travis-ci.org/suminb/finance

.. image:: https://coveralls.io/repos/github/suminb/finance/badge.svg?branch=develop
   :target: https://coveralls.io/github/suminb/finance?branch=develop

NOTE: 제가 주로 사용하는 에디터인 vim 에서 한글 타이핑이 불편하기 때문에 영어로 문서를 작성하는 것이 일반적이지만, 이 프로젝트의 경우 한국어를 사용하는 청중이 대부분인 관계로 문서를 한국어로 작성합니다.

비전
----
`NDC 2016 - 프로그래머가 투자하는 법 <http://www.slideshare.net/suminb/how-programmers-invest>`_


(TODO: NDC에서 이런 발표를 하게 된 계기에 대한 설명 적어놓기)

현재 상태
---------
코드를 보신 분은 아시겠지만, 이 프로젝트는 미완성 상태입니다. 아니, 그냥 미완성 상태가 아니라 시작한지 얼마 되지 않았다고 얘기 하는편이 더 정확하겠군요. 지금 구현된 기능은 다음과 같습니다.

* 데이터베이스 모델: 기본적인 틀은 갖추어졌지만, 아직 부족한 점이 많아 앞으로 점진적으로 개선해 나갈 계획입니다. 데이터베이스 마이그레이션 도구로는 `Alembic <https://pypi.python.org/pypi/Flask-Alembic>`_ 을 사용할 계획입니다.
  * 웹 인터페이스: 지금은 일자별 net asset value를 계산해서 보여주는 것만 겨우 돌아가도록 만들어놓은 상태입니다. 발표용으로 급조한거(...)

앞으로 할 일들
--------------
* 웹 인터페이스: 포트폴리오 구성을 한 눈에 볼 수 있는 인터페이스를 만들 계획입니다.
* 자동으로 데이터 받아오기: 주식, 펀드 가격 등 거래소에 공시되는 가격을 주기적으로 받아오는 무언가를 만들어야 합니다. 사용할 도구로는 AWS Lambda가 적당해보입니다.

(TODO: 내용 계속 채워넣기)
