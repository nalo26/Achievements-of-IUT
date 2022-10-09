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
config.read('dev.config.ini')

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
db.init_config(config)

# @app.before_request
# def limit_remote_addr():
#     if request.remote_addr != config['Flask']['authorized']:
#         abort(403, "Site en maintenance !")

@app.route('/')
@app.route('/achievement')
@app.route('/achievements')
def main():
    return redirect('/0')

@app.route('/achievement/<int:cat_id>')
@app.route('/achievements/<int:cat_id>')
def achievement(cat_id):
    return redirect(f"/{cat_id}")


# ---------------------------------------------------------------------------------------
@app.route('/<int:cat_id>')
def achievements(cat_id):
    achievements_data, _ = read_achievements()
    if cat_id < 0 or cat_id >= len(achievements_data): return redirect('/0')
    session['page'] = f"/{cat_id}"
    
    return render_template('achievements.html', achievements=achievements_data, category=cat_id,
                           login_url=auth.get_login_url(), admin_id=admin.admin_id)
# ---------------------------------------------------------------------------------------

@app.route('/save', methods=['POST'])
def save():
    if not g.user: return api.response({'success': False, 'msg': 'not logged'}, 401)
    
    data = request.json
    user_id = int(data.get('user'))
    ach_id = int(data.get('achievement'))
    if g.user['id_user'] != user_id: return api.response({'success': False, 'msg': 'impersonating'}, 401)
    
    if data.get('type') not in ('add', 'remove'): return api.response({'success': False, 'msg': 'bad action'}, 401)
    
    _, cursor = db.get_db()
    cursor.execute("SELECT * FROM achievement WHERE id_achievement = %s", (ach_id,))
    ach = cursor.fetchone()
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
    
    _, cursor = db.get_db()
    users = []
    
    if year is None:
        session['page'] = "/leaderboard"
        cursor.execute("SELECT * FROM users u JOIN discord_user d USING(id_user) ORDER BY score DESC")
        users = cursor.fetchall()
    else:
        session['page'] = f"/leaderboard/{year}"
        cursor.execute("SELECT * FROM users u JOIN discord_user d USING(id_user) WHERE year = %s ORDER BY score DESC", (year,))
        users = cursor.fetchall()
        
    return render_template('leaderboard.html', users=users, year=year, maxyear=maxyear,
                           login_url=auth.get_login_url(), admin_id=admin.admin_id)


@app.route('/profile/<int:user_id>')
def profile(user_id):
    session['page'] = f"/profile/{user_id}"
    _, cursor = db.get_db()
    cursor.execute("SELECT * FROM users AS u JOIN discord_user d USING(id_user) WHERE u.id_user = %s", (user_id,))
    user = cursor.fetchone()
    if user is None: abort(404, f"No user with ID {user_id} was found.")

    datejoin = user['joindate']
    cursor.execute("SELECT * FROM done WHERE complete = TRUE AND id_user = %s", (user_id,))
    ach_complete = len(cursor.fetchall())
    cursor.execute("SELECT * FROM achievement")
    ach_amount = len(cursor.fetchall())
    
    cursor.execute("SELECT * FROM users ORDER BY score DESC")
    users = [r['id_user'] for r in cursor.fetchall()]
    rank = users.index(user_id) + 1
    
    cursor.execute("SELECT id_user FROM users JOIN discord_user USING(id_user) WHERE year = %s ORDER BY score DESC", (user['year'],))
    year_users = [r['id_user'] for r in cursor.fetchall()]
    year_rank = year_users.index(user_id) + 1

    cursor.execute("SELECT SUM(difficulty) AS data FROM achievement")
    max_score = cursor.fetchone()['data']
    
    cursor.execute("SELECT difficulty, count(difficulty) AS amount " + \
                       "FROM done JOIN achievement USING(id_achievement) " + \
                       "WHERE complete = TRUE AND id_user = %s GROUP BY difficulty " + \
                       "ORDER BY difficulty", (user_id,))
    difficulties = [0]*5
    for r in cursor.fetchall():
        difficulties[r['difficulty']-1] = r['amount']
    
    return render_template('profile.html', user=user, datejoin=datejoin, ach_complete=ach_complete, difficulties=difficulties, 
                           ach_amount=ach_amount, rank=rank, user_amount=len(users), year_rank=year_rank, year_user_amount=len(year_users),
                           max_score=max_score, login_url=auth.get_login_url(), admin_id=admin.admin_id)


@app.route("/stat")
@app.route("/stats")
@app.route("/statistic")
@app.route("/statistics")
def statistics():
    session['page'] = "/statistics"
    _, cursor = db.get_db()
    stats = []

    cursor.execute("SELECT COUNT(id_user) AS data FROM users")
    a = cursor.fetchone()['data']
    cursor.execute("SELECT COUNT(id_user) AS data FROM discord_user")
    s = cursor.fetchone()['data']
    stats.append(("Nombre de participants", f"{a} / {s}"))


    cursor.execute("SELECT AVG(score) AS data FROM users")
    a = cursor.fetchone()['data']
    cursor.execute("SELECT SUM(difficulty) AS data FROM achievement")
    s = cursor.fetchone()['data']
    stats.append(("Score moyen", f"{round(a)} / {s}"))

    cursor.execute("SELECT SUM(score) AS data FROM users")
    res = cursor.fetchone()['data']
    stats.append(("Score cumulé", res))

    cursor.execute("SELECT AVG(c) AS data FROM (SELECT COUNT(id_achievement) AS c FROM done WHERE complete = TRUE GROUP BY id_user) d")
    a = cursor.fetchone()['data']
    cursor.execute("SELECT COUNT(id_achievement) AS data FROM achievement")
    s = cursor.fetchone()['data']
    stats.append(("Nombre moyen d'achievements réalisés", f"{round(a)} / {s}"))

    cursor.execute("SELECT SUM(c) AS data FROM (SELECT COUNT(id_achievement) AS c FROM done WHERE complete = TRUE GROUP BY id_user) d")
    res = cursor.fetchone()['data']
    stats.append(("Nombre cumulé d'achievements réalisés", res))

    cursor.execute("SELECT year, AVG(score) AS avg_score FROM users JOIN discord_user USING(id_user) GROUP BY year ORDER BY avg_score")
    res = cursor.fetchall()
    stats.append(("Meilleure promo (score moyen)", f"{res[-1]['year']} ({round(res[-1]['avg_score'])} pts)"))

    cursor.execute("SELECT id_achievement AS id, COUNT(id_achievement) AS c FROM done JOIN achievement USING(id_achievement) WHERE complete = TRUE GROUP BY id_achievement ORDER BY c DESC")
    res = cursor.fetchone()
    stats.append(("Achievement le plus réalisé", f"x {res['c']}"))

    cursor.execute("SELECT * FROM achievement WHERE id_achievement = %s", (res['id'],))
    ach = cursor.fetchone()

    return render_template('statistics.html', statistics=stats, achievement=ach)

def save_score(action, user_id, ach, allowed=True):
    ach_id = ach['id_achievement']
    connection, cursor = db.get_db()
    
    if action == "add" and allowed:
        cursor.execute("SELECT * FROM done WHERE id_user = %s AND id_achievement = %s", (user_id, ach_id))
        done = cursor.fetchone()
        if done is None:
            cursor.execute("INSERT INTO done  (id_user, id_achievement) VALUES (%s, %s)", (user_id, ach_id,))
            cursor.execute("INSERT INTO event_save_score (id_user, id_achievement) VALUES (%s, %s)", (user_id, ach_id,))
        else:
            cursor.execute("UPDATE done SET complete = TRUE where id_user = %s AND id_achievement = %s", (user_id, ach_id,))
        cursor.execute("UPDATE users SET score = score + %s WHERE id_user = %s", (ach['difficulty'], user_id,))
        connection.commit()
    if action == "remove" and allowed:
        cursor.execute("UPDATE done SET complete = FALSE where id_user = %s AND id_achievement = %s", (user_id, ach_id,))
        cursor.execute("UPDATE users SET score = score - %s WHERE id_user = %s", (ach['difficulty'], user_id,))
        connection.commit()
        
    cursor.execute("SELECT * FROM achievement WHERE id_achievement = %s", (ach['parent_id'],))
    parent = cursor.fetchone()
    if parent is not None:
        _, all_childs_completed = read_achievements(parent['id_achievement'])
        cursor.execute("SELECT * FROM done WHERE id_user = %s AND id_achievement = %s", (user_id, parent['id_achievement']))
        done = cursor.fetchone()
        if all_childs_completed: # add
            allowed = done is None or done is not None and int(done['complete']) == 0
        else: # remove
            allowed = done is not None and int(done['complete']) == 1
        save_score(action, user_id, parent, bool(parent['auto_complete']) and allowed)

def read_achievements(parent_id=None):
    data = []
    connection, cursor = db.get_db()
    query = "SELECT * FROM achievement WHERE parent_id "
    query += "is null" if parent_id is None else f"= {parent_id}"
    all_complete = True
    cursor.execute(query)
    for elem in cursor.fetchall():
        
        childs, all_childs_complete = read_achievements(elem['id_achievement'])
        all_complete = all_complete and all_childs_complete
        
        auto_complete = bool(elem['auto_complete'])
        complete = False
        if g.user:
            cursor.execute("SELECT * FROM done WHERE complete = TRUE AND id_user = %s AND id_achievement = %s", (g.user['id_user'], elem['id_achievement'],))
            user_complete = cursor.fetchone() is not None
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
    app.run(debug=False, host=config['Flask']['host'], port=config['Flask']['port'])