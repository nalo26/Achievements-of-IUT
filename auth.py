import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

bp = Blueprint('auth', __name__)

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


@bp.route('/register', methods=('GET', 'POST'))
def register():
    data = {}
    if request.method == 'POST':
        data = request.form.to_dict(False)
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        password = request.form['password']
        confirm = request.form['confirm']
        year = int(request.form['year'])
        db = get_db()
        error = None

        if not firstname: error = 'Vous devez rentrer un prénom !'
        elif not lastname: error = 'Vous devez rentrer un nom !'
        elif not password: error = 'Vous devez rentrer un mot de passe !'
        elif password != confirm: error = 'Les mots de passe ne sont pas identiques !'
        elif db.execute(
            'SELECT id_user FROM user WHERE firstname = ? and lastname = ?', (firstname, lastname,)
        ).fetchone() is not None:
            error = f"L'utilisateur•rice \"{firstname} {lastname}\" existe déjà !"

        if error is None:
            db.execute(
                'INSERT INTO user (firstname, lastname, password, year) VALUES (?, ?, ?, ?)',
                (firstname, lastname, generate_password_hash(password), year)
            )
            db.commit()
            flash("Inscription réussie, veuillez vous connecter.", 'success')
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
            session['id_user'] = user['id_user']
            return redirect(url_for('achievements', cat_id=0))

        flash(error, 'error')

    return render_template('auth/login.html', title="Connexion", data=data)

@bp.route('/edit', methods=('GET', 'POST'))
@login_required
def edit_profile():
    if request.method == 'POST':
        current_pwd = request.form['current']
        new_pwd = request.form['new']
        confirm_pwd = request.form['confirm']
        db = get_db()
        error = None
        
        if not current_pwd: error = "Vous devez rentrer votre mot de passe actuel !"
        elif not new_pwd: error = "Vous devez rentrer un nouveau mot de passe !"
        elif not confirm_pwd: error = "Vous devez confirmer le nouveau mot de passe !"
        elif not check_password_hash(g.user['password'], current_pwd):
            error = "Erreur dans votre mot de passe actuel !"
        elif check_password_hash(g.user['password'], new_pwd):
            error = "Vous ne pouvez pas rentrer le même mot de passe !"
        elif new_pwd != confirm_pwd: error = "Les mots de passe ne sont pas identiques !"
        
        if error is None:
            db.execute('UPDATE user SET password = ? WHERE id_user = ?',
                      (generate_password_hash(new_pwd), g.user['id_user'],))
            db.commit()
            flash("Changement effectué avec succès", 'success')
        else: flash(error, 'error')
        
    return render_template('auth/edit.html')

@bp.route('/logout')
def logout():
    page = session['page']
    if page is None: page = 0
    session.clear()
    return redirect(url_for('achievements', cat_id=page))


@bp.before_app_request
def load_logged_in_user():
    id_user = session.get('id_user')

    if id_user is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id_user = ?', (id_user,)
        ).fetchone()