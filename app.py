from flask import Flask, redirect, render_template
import json
import os
import db, auth

app = Flask(__name__, instance_relative_config = True)
app.config.from_mapping(
    SECRET_KEY = 'dev',
    DATABASE = os.path.join(app.instance_path, 'database.sqlite'),
)
app.register_blueprint(auth.bp)
db.init_app(app)

# achievements_data = json.loads(open('static/Achievements.json', 'r', encoding='utf-8').read())
achievements_path = 'static/Achievements.json'

@app.route('/')
@app.route('/achievement')
@app.route('/achievements')
def main():
    return redirect(f'/achievements/0')

@app.route('/achievement/<string:cat_name>')
@app.route('/achievements/<string:cat_name>')
def achievements_name(cat_name):
    cat_name = format_string(cat_name)
    for i, d in enumerate(read_json(achievements_path)):
        if cat_name in d["aliases"]: return redirect(f'/achievements/{i}')
    return redirect('/achievements/0')

@app.route('/achievement/<int:cat_id>')
def achievement(cat_id):
    return redirect(f"/achievements/{cat_id}")


# ---------------------------------------------------------------------------------------
@app.route('/achievements/<int:cat_id>')
def achievements(cat_id):
    achievements_data = read_json(achievements_path)
    if cat_id < 0 or cat_id >= len(achievements_data): return redirect('/achievements/0')
    
    return render_template('achievements.html', achievements=achievements_data, category=cat_id)
# ---------------------------------------------------------------------------------------


@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(500)
def error_page(error):
    return f"Error {error.code}", error.code


def format_string(string):
    return string.lower().replace(" ", "_")

def read_json(path):
    data = []
    with open(path, 'r', encoding="utf-8") as mf:
        data = json.load(mf)
    mf.close()
    return data


if __name__ == '__main__':
    app.run(debug = True)