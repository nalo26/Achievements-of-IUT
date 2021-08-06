from sqlite3.dbapi2 import OperationalError, IntegrityError
from flask import Flask, redirect, render_template, session, g, request, abort
import os
import configparser
from datetime import datetime

import db
import auth
import api
import admin

config = configparser.ConfigParser()
config.read('config.ini')

app = Flask(__name__, instance_relative_config = True)
app.config.from_mapping(
    SECRET_KEY = config['Flask']['secret'],
    DATABASE = os.path.join(app.instance_path, 'database.sqlite'),
)

app.register_blueprint(auth.bp)
app.register_blueprint(api.bp)
app.register_blueprint(admin.bp)
auth.init_config(config)
admin.init_config(config)
db.init_app(app)

@app.route('/')
@app.route('/achievement')
@app.route('/achievements')
def main():
    return redirect('/achievements/0')

@app.route('/achievement/<int:cat_id>')
def achievement(cat_id):
    return redirect(f"/achievements/{cat_id}")


# ---------------------------------------------------------------------------------------
@app.route('/achievements/<int:cat_id>')
def achievements(cat_id):
    achievements_data, _ = read_achievements()
    if cat_id < 0 or cat_id >= len(achievements_data): return redirect('/achievements/0')
    session['page'] = f"/achievement/{cat_id}"
    
    return render_template('achievements.html', achievements=achievements_data, category=cat_id, login_url=auth.get_login_url())
# ---------------------------------------------------------------------------------------

@app.route('/save', methods=['POST'])
def save():
    if not g.user: return api.response({'success': False, 'msg': 'not logged'}, 401)
    
    data = request.json
    user_id = int(data.get('user'))
    ach_id = int(data.get('achievement'))
    if g.user['id_user'] != user_id: return api.response({'success': False, 'msg': 'impersonating'}, 401)
    
    if data.get('type') not in ('add', 'remove'): return api.response({'success': False, 'msg': 'bad action'}, 401)
    
    base = db.get_db()
    ach = base.execute("SELECT * FROM achievement WHERE id_achievement = ?", (ach_id,)).fetchone()
    if bool(ach['auto_complete']): return api.response({'success': False, 'msg': 'autocomplete'}, 401)
    
    try:
        save_score(data.get('type'), user_id, ach)  
    except (OperationalError, IntegrityError):
        return api.response({'success': False}, 500)
    
    return api.response({'success': True})


@app.route('/leaderboard', defaults={'year': None})
@app.route('/leaderboard/<int:year>')
def leaderboard(year):
    now = datetime.now()
    month = now.month
    maxyear = now.year
    if month < 7: maxyear -= 1
    if year is not None and (year < 2017 or year > maxyear): return redirect('/leaderboard')
    
    base = db.get_db()
    users = []
    
    if year is None:
        session['page'] = "/leaderboard"
        users = base.execute("SELECT * FROM user u JOIN discord_user d USING(id_user) ORDER BY score DESC").fetchall()
    else:
        session['page'] = f"/leaderboard/{year}"
        users = base.execute("SELECT * FROM user u JOIN discord_user d USING(id_user) WHERE year = ? ORDER BY score DESC",
                             (year,)).fetchall()
        
    return render_template('leaderboard.html', users=users, year=year, maxyear=maxyear, login_url=auth.get_login_url())


@app.route('/profile/<int:user_id>')
def profile(user_id):
    session['page'] = f"/profile/{user_id}"
    base = db.get_db()
    user = base.execute("SELECT * FROM user u JOIN discord_user d USING(id_user) WHERE u.id_user = ?", (user_id,)).fetchone()
    if user is None: abort(404, f"No user with ID {user_id} was found.")

    datejoin = datetime.strptime(user['joindate'], "%Y-%m-%d %H:%M:%S")
    ach_complete = len(base.execute("SELECT * FROM done WHERE id_user = ?", (user_id,)).fetchall())
    ach_amount = len(base.execute("SELECT * FROM achievement").fetchall())
    
    users = [r['id_user'] for r in base.execute("SELECT * FROM user ORDER BY score DESC").fetchall()]
    rank = users.index(user_id) + 1
    
    year_users = [r['id_user'] for r in base.execute(
        "SELECT id_user FROM user JOIN discord_user USING(id_user) WHERE year = ? ORDER BY score DESC", (user['year'],)
        ).fetchall()
    ]
    year_rank = year_users.index(user_id) + 1
    
    req = base.execute("SELECT difficulty, count(difficulty) AS amount " + \
                       "FROM done JOIN achievement USING(id_achievement) " + \
                       "WHERE id_user = ? GROUP BY difficulty " + \
                       "ORDER BY difficulty", (user_id,))
    difficulties = [0]*5
    for r in req.fetchall():
        difficulties[r['difficulty']-1] = r['amount']
    
    return render_template('profile.html', user=user, datejoin=datejoin, ach_complete=ach_complete, difficulties=difficulties, 
                           ach_amount=ach_amount, rank=rank, user_amount=len(users), year_rank=year_rank, year_user_amount=len(year_users),
                           login_url=auth.get_login_url())


def save_score(action, user_id, ach, allowed=True):
    ach_id = ach['id_achievement']
    base = db.get_db()
    
    if action == "add" and allowed:
        done = base.execute("SELECT * FROM done WHERE id_user = ? AND id_achievement = ?", (user_id, ach_id)).fetchone()
        if done is None:
            base.execute("INSERT INTO done  (id_user, id_achievement) VALUES (?, ?)", (user_id, ach_id,))
            base.execute("INSERT INTO event (id_user, id_achievement) VALUES (?, ?)", (user_id, ach_id,))
        else:
            base.execute("UPDATE done SET complete = 1 where id_user = ? AND id_achievement = ?", (user_id, ach_id,))
        base.execute("UPDATE user SET score = score + ? WHERE id_user = ?", (ach['difficulty'], user_id,))
        base.commit()
    if action == "remove" and allowed:
        base.execute("UPDATE done SET complete = 0 where id_user = ? AND id_achievement = ?", (user_id, ach_id,))
        base.execute("UPDATE user SET score = score - ? WHERE id_user = ?", (ach['difficulty'], user_id,))
        base.commit()
        
    parent = base.execute("SELECT * FROM achievement WHERE id_achievement = ?", (ach['parent_id'],)).fetchone()
    if parent is not None:
        _, all_childs_completed = read_achievements(parent['id_achievement'])
        if all_childs_completed: save_score("add", user_id, parent, bool(parent['auto_complete']))
        else: save_score("remove", user_id, parent, bool(parent['auto_complete']))

def read_achievements(parent_id=None):
    data = []
    base = db.get_db()
    query = "SELECT * FROM achievement WHERE parent_id "
    query += "is null" if parent_id is None else f"= {parent_id}"
    all_complete = True
    for elem in base.execute(query).fetchall():
        
        childs, all_childs_complete = read_achievements(elem['id_achievement'])
        all_complete = all_complete and all_childs_complete
        
        auto_complete = bool(elem['auto_complete'])
        complete = False
        if g.user: 
            user_complete = base.execute("SELECT * FROM done WHERE complete = 1 AND id_user = ? AND id_achievement = ?", 
                                        (g.user['id_user'], elem['id_achievement'],)).fetchone() is not None
            if not user_complete: all_complete = False
            complete = all_childs_complete if auto_complete else user_complete
        else: all_complete = False
            
        ach = {
            "id": elem['id_achievement'],
            "name": elem['name'],
            "lore": elem['lore'],
            "difficulty": elem['difficulty'],
            "auto_complete": int(auto_complete),
            "complete": int(complete)
        }
        if len(childs) > 0: ach['childs'] = childs
        data.append(ach)
    return data, all_complete
    

if __name__ == '__main__':
    app.run(debug=True, host=config['Flask']['host'], port=config['Flask']['port'])