from flask import Blueprint, request, redirect

from db import get_db

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/')
def default():
    return redirect("https://github.com/nalo26/Achievements-of-IUT/blob/main/api.md")

@bp.route('/get_user')
def user():
    try:
        user_id = request.args.get('id')
        if user_id is None: return response()
            
        base = get_db()
        
        u = base.execute("SELECT * FROM user WHERE id_user = ?", (user_id,)).fetchone()
        if u is None: return response()
        
        req = base.execute("SELECT difficulty, count(difficulty) AS amount " + \
                        "FROM done JOIN achievement USING(id_achievement) " + \
                        "WHERE id_user = ? GROUP BY difficulty " + \
                        "ORDER BY difficulty", (user_id,))
        difficulties = [0]*5
        for r in req.fetchall():
            difficulties[r['difficulty']-1] = r['amount']
            
        users = [r['id_user'] for r in base.execute("SELECT * FROM user ORDER BY score DESC").fetchall()]
        rank = users.index(int(user_id)) + 1
        
        year_users = [r['id_user'] for r in base.execute("SELECT id_user FROM user WHERE year = ? ORDER BY score DESC", (u['year'],)).fetchall()]
        year_rank = year_users.index(int(user_id)) + 1
        
        ret = {
            "id_user"                : u['id_user'],        
            "firstname"              : u['firstname'],
            "lastname"               : u['lastname'],
            "promotion_year"         : u['year'],
            "join_date"              : u['joindate'],
            "score"                  : u['score'],
            "count_easy"             : difficulties[0],
            "count_normal"           : difficulties[1],
            "count_hard"             : difficulties[2],
            "count_hardcore"         : difficulties[3],
            "count_impossible"       : difficulties[4],
            "global_rank"            : rank,
            "year_rank"              : year_rank,
            "completed_achievements" : [
                r['id_achievement'] for r in base.execute("SELECT id_achievement FROM done WHERE id_user = ?", (user_id,)).fetchall()
            ]
        }
        return response(ret)
    except Exception: return response()

@bp.route('/get_achievement')
def achievement():
    try:
        ach_id = request.args.get('id')
        if ach_id is None: return response()
            
        base = get_db()
        
        a = base.execute("SELECT * FROM achievement WHERE id_achievement = ?", (ach_id,)).fetchone()
        if a is None: return response()
        
        ret = {
            "id_achievement" : a['id_achievement'],
            "name"           : a['name'],
            "lore"           : a['lore'],
            "difficulty"     : a['difficulty'],
            "auto_complete"  : a['auto_complete'],
            "childs"         : [
                r['id_achievement'] for r in base.execute("SELECT id_achievement FROM achievement WHERE parent_id = ?", (a['id_achievement'],)).fetchall()
            ]
        }
        return response(ret)
    except Exception: return response()

@bp.route('/get_leaderboard')
def leaderboard():
    try:
        year = request.args.get('year')
        
        base = get_db()
        
        leaderboard = None
        if year is None:
            leaderboard = base.execute("SELECT * FROM user u JOIN discord_user d USING(id_user) ORDER BY score DESC").fetchall()
        else:
            leaderboard = base.execute("SELECT * FROM user u JOIN discord_user d USING(id_user) WHERE year = ? ORDER BY score DESC", (year,)).fetchall()
        if leaderboard is None: return response()
        
        ret = {
            "year"  : 0 if year is None else int(year),
            "users" : [
                {
                    "id_user"        : u['id_user'],
                    "name"           : f"{u['firstname']} {u['lastname']}",
                    "promotion_year" : u['year'],
                    "score"          : u['score'],
                }
                for u in leaderboard
            ]
        }
        return response(ret)
    except Exception: return response()

def response(data=None, code=200):
    if data is None: data = {}
    return data, code, {'ContentType':'application/json'}