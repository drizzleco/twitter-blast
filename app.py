from flask_sqlalchemy import SQLAlchemy
from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    session,
    redirect,
    url_for,
    flash,
)
from flask_cors import CORS
from secrets import HOSTED_CONSUMER_KEY, HOSTED_CONSUMER_SECRET, SECRET_KEY
import tweepy
from flask import Flask
from models import User, Follower, db
import twitter_blast


app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///twitter_blast.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = SECRET_KEY
db.app = app
db.init_app(app)

auth = tweepy.OAuthHandler(
    HOSTED_CONSUMER_KEY, HOSTED_CONSUMER_SECRET, "http://127.0.0.1:5000"
)


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
        user = User(username=username)
        db.session.add(user)
        db.session.commit()
    rank_by = request.args.get("rank_by")
    if not rank_by:
        rank_by = "recent"
    value = request.args.get("value")
    if not value:
        value = ""
    has_fetched_followers = user.followers
    try:
        dms_all_sent = False
        followers = twitter_blast.ranked_followers(
            username, rank_by=rank_by, value=value
        )
    except:
        dms_all_sent = True
        followers = None
    if username:
        return render_template(
            "index.html",
            username=username,
            dms_all_sent=dms_all_sent,
            has_fetched_followers=has_fetched_followers,
            followers=followers,
            ranking_choices=twitter_blast.ranking_choices,
            rank_by=rank_by,
            value=value,
        )


@app.route("/fetch", methods=["POST"])
def fetch():
    api = tweepy.API(auth)
    username = api.me().screen_name
    twitter_blast.fetch_followers(username, api)
    return redirect(url_for("home"))


@app.route("/send", methods=["POST"])
def send():
    api = tweepy.API(auth)
    username = tweepy.API(auth).me().screen_name
    message = request.form.get("message")
    if not message:
        flash("Your message can't be empty!")
        return redirect(url_for("home"))
    real = request.form.get("real", False)
    rank_by = request.form.get("rank_by", "recent")
    value = request.form.get("value", "")
    twitter_blast.mass_dm_followers(username, message, rank_by, value, not real, api)
    if real:
        flash("Mass DM sent!")
    else:
        flash("Mass DM sent! Dry run was ON, so messages weren't actually sent!")
    return redirect(url_for("home"))


@app.route("/reset", methods=["POST"])
def reset():
    username = tweepy.API(auth).me().screen_name
    twitter_blast.handle_reset(username)
    return redirect(url_for("home"))


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
