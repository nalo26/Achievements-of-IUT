from flask import Flask, redirect, render_template
import json
import urllib.parse
app = Flask(__name__)

achievements_data = json.loads(open('static/Achievements.json', 'r', encoding='utf-8').read())

@app.route('/')
@app.route('/achievement')
@app.route('/achievements')
def main():
    return redirect(f'/achievements/0')

@app.route('/achievement/<string:cat_name>')
@app.route('/achievements/<string:cat_name>')
def achievements_name(cat_name):
    cat_name = format_string(cat_name)
    for i, d in enumerate(achievements_data):
        if cat_name in d["alternates"]: return redirect(f'/achievements/{i}')
    return redirect('/achievements/0')

@app.route('/achievement/<int:cat_id>')
def achievement(cat_id):
    return redirect(f"/achievements/{cat_id}")

@app.route('/achievements/<int:cat_id>')
def achievements(cat_id):
    return render_template('achievements.html', achievements=achievements_data)

@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(500)
def error_page(error):
    return f"Error {error.code}", error.code


def format_string(string):
    return string.lower().replace(" ", "_")


if __name__ == '__main__':
    app.run(debug = True)