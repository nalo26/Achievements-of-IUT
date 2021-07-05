from flask import Flask, redirect, render_template
import json
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
    
    return render_template('achievements.html')

@app.route('/achievement/<int:cat_id>')
@app.route('/achievements/<int:cat_id>')
def achievements(cat_id):
    
    return render_template('achievements.html', achievements=achievements_data)

@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(500)
def error_page(error):
    return f"Error {error.code}", error.code


if __name__ == '__main__':
    app.run(debug = True)