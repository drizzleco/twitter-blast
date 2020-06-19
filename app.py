from flask_sqlalchemy import SQLAlchemy
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
from secrets import CONSUMER_KEY, CONSUMER_SECRET, SECRET_KEY
import tweepy
from flask import Flask
from models import User, Follower, db
import tweet_blast


app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tweet_blast.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = SECRET_KEY
db.app = app
db.init_app(app)

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, "http://127.0.0.1:5000")
api = None
username = ""


@app.route("/")
def home():
    token = request.args.get("oauth_token")
    verifier = request.args.get("oauth_verifier")
    access_token = session.get("access_token")
    access_token_secret = session.get("access_token_secret")
    if token:
        # oauth redirect
        auth.request_token = {
            "oauth_token": token,
            "oauth_token_secret": verifier,
        }
        try:
            auth.get_access_token(verifier)
            session["access_token"] = auth.access_token
            session["access_token_secret"] = auth.access_token_secret
        except tweepy.TweepError:
            print("Error! Failed to get access token.")
    elif access_token:
        # token already stored in session
        auth.set_access_token(access_token, access_token_secret)
    else:
        # sign in prompt
        redirect_url = auth.get_authorization_url()
        return render_template("index.html", redirect_url=redirect_url)
    api = tweepy.API(auth)
    username = api.me().screen_name
    user = User.query.filter_by(username=username).first()
    if not user:
        # create user
        db.session.add(User(username=username))
        db.session.commit()
    followers = User.query.filter_by(username=username).first().followers
    if username:
        return render_template("index.html", username=username, followers=followers)


@app.route("/fetch", methods=["POST"])
def fetch():
    api = tweepy.API(auth)
    tweet_blast.fetch_followers(api)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
