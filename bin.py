import click

from finance.models import db


@click.group()
def cli():
    pass


@cli.command()
def create_all():
    from finance import create_app
    app = create_app(__name__)
    with app.app_context():
        db.create_all()


@cli.command()
def drop_all():
    from finance import create_app
    app = create_app(__name__)
    with app.app_context():
        db.drop_all()


if __name__ == '__main__':
    cli()
