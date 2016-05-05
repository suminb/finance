from flask import Blueprint, jsonify, render_template, request
from logbook import Logger

from finance.models import Account, Asset, Portfolio
from finance.utils import date_range

main_module = Blueprint('main', __name__, template_folder='templates')
log = Logger()


ENTITY_CLASSES = {
    'account': Account,
    'asset': Asset,
    'portfolio': Portfolio,
}


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


@main_module.route('/portfolios/<int:entity_id>')
def view_portfolio(entity_id):
    entity = Portfolio.query.get(entity_id)
    context = {'entity': entity}
    return render_template('view_portfolio.html', **context)


@main_module.route('/entities/<entity_type>')
def list_entities(entity_type):
    entity_class = ENTITY_CLASSES[entity_type]
    entities = entity_class.query.all()
    context = {
        'entities': entities,
    }
    return render_template('list_entities.html', **context)


@main_module.route('/entities/<entity_type>:<int:entity_id>')
def view_entity(entity_type, entity_id):
    entity_class = ENTITY_CLASSES[entity_type]
    entity = entity_class.query.get(entity_id)
    context = {
        'entity': entity,
    }
    return render_template('view_entity.html', **context)
