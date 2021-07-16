from flask import Blueprint, request

from db import get_db

bp = Blueprint('api', __name__, url_prefix='/api')

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
                int(r['id_achievement']) for r in base.execute("SELECT id_achievement FROM done WHERE id_user = ?", (user_id,)).fetchall()
            ]
        }
        return response(ret)
    except Exception as e: return response()

@bp.route('/get_achievement')
def achievement():
    return {}, 200, {'ContentType':'application/json'}

@bp.route('/get_leaderboard')
def leaderboard():
    return {}, 200, {'ContentType':'application/json'}

def response(data=None, code=200):
    if data is None: data = {}
    return data, code, {'ContentType':'application/json'}