from flask import Blueprint, redirect, request, g, url_for
from sqlite3 import OperationalError, IntegrityError
import functools

from flask.templating import render_template

from auth import get_last_page
from db import get_db
from api import response

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

@bp.route('/achievements', methods=('GET', 'POST'))
@admin_required
def manage_achievements():
    base = get_db()
    
    if request.method == 'POST':
        last_a_id = ""
        for key, value in request.form.items():
            k, a_id = key.split('-')
            if k not in ('name', 'lore', 'difficulty'): continue
            if a_id != last_a_id:
                ach = base.execute("SELECT name, lore, difficulty FROM achievement where id_achievement = ?", (a_id,)).fetchone()
            last_a_id = a_id
            if str(ach[k]) == str(value): continue
            base.execute(f"UPDATE achievement SET {k} = ? WHERE id_achievement = ?", (value, a_id,))
            if k == 'difficulty':
                base.execute(
                    f"UPDATE user SET score = score-{ach['difficulty']}+{value} WHERE id_user in (" + \
                    "SELECT id_user FROM done WHERE complete = 1 AND id_achievement = ?" + \
                    ")", (a_id,)
                )
        base.commit()
        
    achievements = base.execute("SELECT * FROM achievement").fetchall()
    return render_template("admin/achievements_manage.html", achievements=achievements, admin_id=admin_id)

@bp.route('/create')
@admin_required
def _create_achievement():
    return redirect(url_for('admin.manage_achievements'))
    
@bp.route('/create/<int:parent_id>', methods=['GET', 'POST'])
@admin_required
def create_achievement(parent_id):
    base = get_db()
    parent = base.execute("SELECT * FROM achievement WHERE id_achievement = ?", (parent_id,)).fetchone()
    if parent is None: return redirect(url_for('admin.manage_achievements'))
    
    data = {}
    if request.method == 'POST':
        data = request.form.to_dict(False)
        auto = bool(request.form.get('auto') is not None) 
        base.execute("INSERT INTO achievement (name, lore, difficulty, parent_id, auto_complete)" +\
                     "VALUES (?, ?, ?, ?, ?)",
                     (request.form['name'], request.form['lore'], request.form['difficulty'], parent_id, auto,))
        base.commit()
        return redirect(url_for('admin.manage_achievements'))
        
    
    return render_template("admin/create.html", data=data, parent=parent['name'], admin_id=admin_id)


@bp.route('/delete', methods=['POST'])
@admin_required
def delete():
    if not g.user: return response({'success': False, 'msg': 'not logged'}, 401)
    
    data = request.json
    ach_id = int(data.get('id'))
    
    base = get_db()
    ach = base.execute("SELECT * FROM achievement WHERE id_achievement = ?", (ach_id,)).fetchone()
        
    try:
        delete_achievement(ach['id_achievement'], ach['difficulty'])  
    except (OperationalError, IntegrityError):
        return response({'success': False}, 500)
    
    return response({'success': True})


def delete_achievement(ach_id, dif):
    base = get_db()
    childs = base.execute("SELECT id_achievement, difficulty FROM achievement WHERE parent_id = ?", (ach_id,)).fetchall()
    for child in childs:
        delete_achievement(child['id_achievement'], child['difficulty'])
    
    base.execute(
        f"UPDATE user SET score = score-{dif} WHERE id_user in (" + \
        "SELECT id_user FROM done WHERE complete = 1 AND id_achievement = ?" + \
        ")", (ach_id,)
    )
    base.execute("DELETE FROM done WHERE id_achievement = ?", (ach_id,))
    base.execute("DELETE FROM event WHERE id_achievement = ?", (ach_id,))
    base.execute("DELETE FROM achievement WHERE id_achievement = ?", (ach_id,))
    base.commit()