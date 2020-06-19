from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # shared db instance


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_str = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String)
    screen_name = db.Column(db.String)
    location = db.Column(db.String)
    description = db.Column(db.Text)
    followers_count = db.Column(db.Integer)
    friends_count = db.Column(db.Integer)
    listed_count = db.Column(db.Integer)
    favourites_count = db.Column(db.Integer)
    statuses_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime)
    verified = db.Column(db.Boolean)
    dm_sent = db.Column(db.Boolean, default=False)
