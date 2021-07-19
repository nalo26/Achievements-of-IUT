import functools
import os
from requests_oauthlib import OAuth2Session
from flask import Blueprint, g, redirect, request, session, url_for

from db import get_db

bp = Blueprint('auth', __name__)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

base_discord_api_url = 'https://discordapp.com/api'
client_id = ""
client_secret = ""
redirect_uri = ""
scope = ['identify', 'guilds']
token_url = 'https://discordapp.com/api/oauth2/token'
authorize_url = 'https://discordapp.com/api/oauth2/authorize'


def init_config(config):
    global client_id, client_secret, redirect_uri
    client_id = config['Discord']['client_id']
    client_secret = config['Discord']['client_secret']
    redirect_uri = config['Discord']['redirect_uri']

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(get_login_url())

        return view(**kwargs)

    return wrapped_view


@bp.route('/login_success')
def oauth_callback():
    try:
        discord = OAuth2Session(client_id, redirect_uri=redirect_uri, state=session['state'], scope=scope)
        token = discord.fetch_token(
            token_url,
            client_secret=client_secret,
            authorization_response=request.url,
        )
        session['discord_token'] = token
        return redirect(get_last_page())
    except Exception: return redirect(get_login_url())


@bp.route('/logout')
def logout():
    page = get_last_page()
    session.clear()
    return redirect(page)


@bp.before_app_request
def load_logged_in_user():
    token = session.get('discord_token')

    if token is None:
        g.user = None
    else:
        discord = OAuth2Session(client_id, token=session['discord_token'])
        response = discord.get(base_discord_api_url + '/users/@me')
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id_user = ?', (response.json()['id'],)
        ).fetchone()
        

def get_login_url():
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    login_url, state = oauth.authorization_url(authorize_url)
    session['state'] = state
    return login_url


def get_last_page():
    page = session['page']
    if page is None: page = url_for("/achievements", cat_id=0)
    return page