from flask import Blueprint, redirect, request, g
import functools

from flask.templating import render_template

from auth import get_last_page
from db import get_db

bp = Blueprint('admin', __name__, url_prefix='/admin')

admin_id = None

def init_config(config):
    global admin_id
    admin_id = int(config['DiscordApp']['admin_discord_id'])

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user['id_user'] != admin_id: 
            return redirect(get_last_page())

        return view(**kwargs)

    return wrapped_view

@bp.route('/users', methods=('GET', 'POST'))
@admin_required
def manage_users():
    base = get_db()
    
    if request.method == 'POST':
        last_u_id = ""
        for key, value in request.form.items():
            k, u_id = key.split('-')
            if k not in ('firstname', 'lastname', 'year'): continue
            if u_id != last_u_id:
                user = base.execute("SELECT firstname, lastname, year FROM discord_user where id_user = ?", (u_id,)).fetchone()
            last_u_id = u_id
            if str(user[k]) == str(value): continue
            base.execute(f"UPDATE discord_user SET {k} = ? WHERE id_user = ?", (value, u_id,))
        base.commit()
        
    users = base.execute("SELECT * FROM user u JOIN discord_user d USING(id_user)").fetchall()
    return render_template("admin/users_manage.html", users=users, admin_id=admin_id)

@bp.route('/achievements')
@admin_required
def manage_achievements():
    base = get_db()
    achievements = base.execute("SELECT * FROM achievement").fetchall()
    
    return render_template("admin/achievements_manage.html", achievements=achievements, admin_id=admin_id)