from sqlite3.dbapi2 import OperationalError
from flask import Flask, redirect, render_template, session, g, request, abort
import os
from datetime import datetime

import db
import auth
import api

app = Flask(__name__, instance_relative_config = True)
app.config.from_mapping(
    SECRET_KEY = open('key.txt').read(),
    DATABASE = os.path.join(app.instance_path, 'database.sqlite'),
)
app.register_blueprint(auth.bp)
app.register_blueprint(api.bp)
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
    session['page'] = cat_id
    
    return render_template('achievements.html', achievements=achievements_data, category=cat_id)
# ---------------------------------------------------------------------------------------

# TODO : set to done if complete an auto compelete one
@app.route('/save', methods=['POST'])
def save_score():
    if not g.user: return {'success': False}, 409, {'ContentType':'application/json'}
    
    data = request.json
    if g.user['id_user'] != data.get('user'): return {'success': False}, 409, {'ContentType':'application/json'}
    
    if data.get('type') not in ('add', 'remove'): return {'success': False}, 409, {'ContentType':'application/json'}
    
    base = db.get_db()
    ach = base.execute("SELECT * FROM achievement WHERE id_achievement = ?", (data.get('achievement'),)).fetchone()
    if bool(ach['auto_complete']): return {'success': False}, 409, {'ContentType':'application/json'}
    
    try:
        if data.get('type') == "add":
            base.execute("INSERT INTO done (id_user, id_achievement) VALUES (?, ?)", (data.get('user'), data.get('achievement'),))
            base.execute("UPDATE user SET score = score + ? WHERE id_user = ?", (ach['difficulty'], data.get('user'),))
            base.commit()
        if data.get('type') == "remove":
            base.execute("DELETE FROM done WHERE id_user = ? AND id_achievement = ?", (data.get('user'), data.get('achievement'),))
            base.execute("UPDATE user SET score = score - ? WHERE id_user = ?", (ach['difficulty'], data.get('user'),))
            base.commit()
    except OperationalError:
        return {'success': False}, 500, {'ContentType':'application/json'}
    
    return {'success': True}, 200, {'ContentType':'application/json'}


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
        users = base.execute("SELECT * FROM user ORDER BY score DESC").fetchall()
    else:
        session['page'] = f"/leaderboard/{year}"
        users = base.execute("SELECT * FROM user WHERE year = ? ORDER BY score DESC", (year,)).fetchall()
        
    return render_template('leaderboard.html', users=users, year=year, maxyear=maxyear)


@app.route('/profile/<int:user_id>')
def profile(user_id):
    session['page'] = f"/profile/{user_id}"
    base = db.get_db()
    user = base.execute("SELECT * FROM user WHERE id_user = ?", (user_id,)).fetchone()
    if user is None: abort(404, f"Aucun utilisateur avec l'ID {user_id} n'a été trouvé !")

    datejoin = datetime.strptime(user['joindate'], "%Y-%m-%d %H:%M:%S")
    ach_complete = len(base.execute("SELECT * FROM done WHERE id_user = ?", (user_id,)).fetchall())
    ach_amount = len(base.execute("SELECT * FROM achievement").fetchall())
    
    users = [r['id_user'] for r in base.execute("SELECT * FROM user ORDER BY score DESC").fetchall()]
    rank = users.index(user_id) + 1
    
    year_users = [r['id_user'] for r in base.execute("SELECT id_user FROM user WHERE year = ? ORDER BY score DESC", (user['year'],)).fetchall()]
    year_rank = year_users.index(user_id) + 1
    
    req = base.execute("SELECT difficulty, count(difficulty) AS amount " + \
                       "FROM done JOIN achievement USING(id_achievement) " + \
                       "WHERE id_user = ? GROUP BY difficulty " + \
                       "ORDER BY difficulty", (user_id,))
    difficulties = [0]*5
    for r in req.fetchall():
        difficulties[r['difficulty']-1] = r['amount']
    
    return render_template('auth/profile.html', user=user, datejoin=datejoin, ach_complete=ach_complete, difficulties=difficulties, 
                           ach_amount=ach_amount, rank=rank, user_amount=len(users), year_rank=year_rank, year_user_amount=len(year_users))


@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(500)
def error_page(error):
    return f"Error {error.code}", error.code


def read_achievements(parent_id=None):
    data = []
    base = db.get_db()
    query = "SELECT * FROM achievement WHERE parent_id "
    query += "is null" if parent_id is None else f"= {parent_id}"
    all_complete = True
    for elem in base.execute(query).fetchall():
        
        childs, all_childs_complete = read_achievements(elem['id_achievement'])
        
        auto_complete = bool(elem['auto_complete'])
        complete = False
        if g.user: 
            user_complete = base.execute("SELECT * FROM done WHERE id_user = ? AND id_achievement = ?", 
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
    app.run(debug = True)