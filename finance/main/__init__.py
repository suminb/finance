from flask import Blueprint, render_template

main_module = Blueprint('main', __name__, template_folder='templates')


@main_module.route('/')
def index():
    return render_template('index.html')
