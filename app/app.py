import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    return '<p>Hello World!</p>'

@app.route('/health')
def get_health_status():
    return {"status": "ok"}

@app.route('/version')
def get_version():
    return {"version": os.environ.get("COMMIT_SHA", "unknown")}