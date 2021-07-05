from flask import Flask, redirect, render_template, request
app = Flask(__name__)

@app.route('/')
@app.route('/achievements')
def main():
    return redirect('/achievements/dab')