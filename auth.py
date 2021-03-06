import os
from requests_oauthlib import OAuth2Session
from flask import Blueprint, g, redirect, request, session, url_for
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError

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
guild_id = ""


def init_config(config):
    global client_id, client_secret, redirect_uri, guild_id
    client_id = config['DiscordApp']['client_id']
    client_secret = config['DiscordApp']['client_secret']
    redirect_uri = config['DiscordApp']['base_uri'] + config['DiscordApp']['redirect_uri']
    guild_id = config['DiscordBot']['guild_id']


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
        discord_user = get_discord_user(token)
        db = get_db()
        user = db.execute("SELECT * FROM user WHERE id_user = ?", (discord_user['id'],)).fetchone()
        if user is None: # register
            if db.execute("SELECT * FROM discord_user WHERE id_user = ?", (discord_user['id'],)).fetchone() is None:
                return "Please make sure to join the discord server before registering."
            db.execute('INSERT INTO user (id_user) VALUES (?)', (discord_user['id'],))
            db.commit()
        # login
        g.user = db.execute("SELECT * FROM user u JOIN discord_user d USING(id_user) WHERE u.id_user = ?",
                            (discord_user['id'],)).fetchone()
        return redirect(get_last_page())
    except Exception as e:
        return redirect(get_login_url())


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
        # print(token)
        try:
            g.user = get_db_user_by_id(get_discord_user(token)['id'])
        except TokenExpiredError:        
            token = refresh_token()
            g.user = get_db_user_by_id(get_discord_user(token)['id'])
            

def refresh_token():
    token = session['discord_token']

    extra = {
        'client_id': client_id,
        'client_secret': client_secret,
    }

    def token_updater(token):
        session['discord_token'] = token

    discord = OAuth2Session(client_id, token=token, auto_refresh_kwargs=extra,
                            auto_refresh_url=token_url, token_updater=token_updater)

    discord.get(base_discord_api_url + '/users/@me')
    return session['discord_token']


def get_discord_user(token):
    discord = OAuth2Session(client_id, token=token)
    response = discord.get(base_discord_api_url + '/users/@me')
    user = response.json()
    return user


def get_db_user_by_id(user_id):
    return get_db().execute(
        "SELECT * FROM user u JOIN discord_user d USING(id_user) WHERE u.id_user = ?", (user_id,)
    ).fetchone()


def get_login_url():
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    login_url, state = oauth.authorization_url(authorize_url)
    session['state'] = state
    return login_url


def get_last_page():
    page = session.get('page')
    if page is None: page = url_for("achievements", cat_id=0)
    return page