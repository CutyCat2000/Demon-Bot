from flask import Flask, render_template, request, send_file
from config import *

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/', methods=['GET'])
def homepage():
    return render_template('home/index.html')

@app.context_processor
def config():
    return dict(bot = {
        "name": bot_name,
        "avatar": bot_avatar,
        "id": bot_id,
        "secret": bot_secret
    })

@app.route('/robots.txt')
def serve_file():
    return send_file('robots.txt')