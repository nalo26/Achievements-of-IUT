import psycopg2
import psycopg2.extras
import click
from flask import current_app, g
from flask.cli import with_appcontext

HOST = ""
DATABASE = ""
USERNAME = ""
PASSWORD = ""

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


def init_config(config):
    global HOST, DATABASE, USERNAME, PASSWORD
    HOST = config['Database']['host']
    DATABASE = config['Database']['base']
    USERNAME = config['Database']['user']
    PASSWORD = config['Database']['pass']


def init_db():
    connection, _ = get_db()

    with current_app.open_resource('schema.sql') as f:
        connection.execute(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def get_db():
    if 'db_connected' not in g:
        connection = psycopg2.connect(
            host=HOST,
            database=DATABASE,
            user=USERNAME,
            password=PASSWORD
        )
        g.connection = connection
        g.cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        g.db_connected = True
    return g.connection, g.cursor


def close_db(e=None):
    cursor = g.pop('cursor', None)
    if cursor is not None:
        cursor.close()
        
    connection = g.pop('connection', None)
    if connection is not None:
        connection.close()