from sqlite3.dbapi2 import OperationalError
from flask import Flask, redirect, render_template, session, g, request
import os

import db
import auth

app = Flask(__name__, instance_relative_config = True)
app.config.from_mapping(
    SECRET_KEY = 'dev',
    DATABASE = os.path.join(app.instance_path, 'database.sqlite'),
)
app.register_blueprint(auth.bp)
db.init_app(app)

@app.route('/')
@app.route('/achievement')
@app.route('/achievements')
def main():
    return redirect(f'/achievements/0')

@app.route('/achievement/<string:cat_name>')
@app.route('/achievements/<string:cat_name>')
def achievements_name(cat_name):
    cat_name = format_string(cat_name)
    for i, d in enumerate(read_achievements()):
        if cat_name in d["aliases"]: return redirect(f'/achievements/{i}')
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
            base.commit()
        if data.get('type') == "remove":
            base.execute("DELETE FROM done WHERE id_user = ? AND id_achievement = ?", (data.get('user'), data.get('achievement'),))
            base.commit()
    except OperationalError:
        return {'success': False}, 500, {'ContentType':'application/json'}
    
    return {'success': True}, 200, {'ContentType':'application/json'}

@app.route('/test')
def test():
    return str(read_achievements()[0])
@app.route('/leaderboard')
def leaderboard():
    return "ahah leaderboard goes brrrr"

@app.route('/profile')
@auth.login_required
def profile():
    return "ahah here's your profile brrrr"

@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(500)
def error_page(error):
    return f"Error {error.code}", error.code


def format_string(string):
    return string.lower().replace(" ", "_")

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