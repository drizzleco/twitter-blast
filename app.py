from flask_sqlalchemy import SQLAlchemy
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///followers.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
