from flask import Blueprint, jsonify, render_template, request
from logbook import Logger

from finance.models import Portfolio
from finance.utils import date_range

main_module = Blueprint('main', __name__, template_folder='templates')
log = Logger()


@main_module.route('/')
def index():
    portfolio = Portfolio.query.first()
    start, end = map(request.args.get, ['start', 'end'])
    context = {
        'portfolio': portfolio,
        'start': start,
        'end': end,
    }
    return render_template('index.html', **context)


@main_module.route('/data')
def data():
    portfolio = Portfolio.query.first()
    start, end = map(request.args.get, ['start', 'end'])
    def gen(start, end):
        for date in date_range(start, end):
            log.info('Calculating net worth on {}', date)
            nw = portfolio.net_worth(date)
            v = float(nw)
            yield date.strftime('%Y%m%d'), v, v, v, v, 0

    return jsonify({'data': [x for x in gen(start, end)]})
