import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=('GET', 'POST'))
def register():
    data = {}
    if request.method == 'POST':
        data = request.form.to_dict(False)
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        password = request.form['password']
        confirm = request.form['confirm']
        db = get_db()
        error = None

        if not firstname: error = 'Vous devez rentrer un prénom !'
        elif not lastname: error = 'Vous devez rentrer un nom !'
        elif not password: error = 'Vous devez rentrer un mot de passe !'
        elif password != confirm: error = 'Les mots de passe ne sont pas identiques !'
        elif db.execute(
            'SELECT id FROM user WHERE firstname = ? and lastname = ?', (firstname, lastname,)
        ).fetchone() is not None:
            error = f"L'utilisateur•rice \"{firstname} {lastname}\" existe déjà !"

        if error is None:
            db.execute(
                'INSERT INTO user (firstname, lastname, password) VALUES (?, ?, ?)',
                (firstname, lastname, generate_password_hash(password))
            )
            db.commit()
            return redirect(url_for('auth.login'))

        flash(error, 'error')

    return render_template('auth/register.html', title="Inscription", data=data)


@bp.route('/login', methods=('GET', 'POST'))
def login():
    data = {}
    if request.method == 'POST':
        data = request.form.to_dict(False)
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE firstname = ? and lastname = ?', (firstname, lastname,)
        ).fetchone()

        if user is None:
            if not firstname: error = 'Vous devez rentrer un prénom !'
            elif not lastname: error = 'Vous devez rentrer un nom !'
            else: error = f"L'utilisateur•rice \"{firstname} {lastname}\" n'est pas inscrit•e !"
        elif not check_password_hash(user['password'], password):
            error = 'Mot de passe incorrect !'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('achievements'))

        flash(error, 'error')

    return render_template('auth/login.html', title="Connexion", data=data)


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('achievements'))


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

        
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view