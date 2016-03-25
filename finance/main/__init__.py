from flask import Blueprint, jsonify, render_template

from finance.models import Portfolio
from finance.utils import date_range

main_module = Blueprint('main', __name__, template_folder='templates')


@main_module.route('/')
def index():
    portfolio = Portfolio.query.first()
    context = {
        'portfolio': portfolio,
        'date_range': date_range('2016-01-01', '2016-02-28'),
    }
    return render_template('index.html', **context)


@main_module.route('/data')
def data():
    portfolio = Portfolio.query.first()
    start, end = '2016-01-01', '2016-02-28'
    def gen(start, end):
        for date in date_range(start, end):
            nw = portfolio.net_worth(date)
            v = float(nw)
            yield date.strftime('%Y%m%d'), v, v, v, v, 0

    return jsonify({'data': [x for x in gen(start, end)]})
