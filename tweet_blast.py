from secrets import CONSUMER_KEY, CONSUMER_SECRET
import tweepy, time, argparse, os, pickle
from models import User, db
from helpers import bye, print_progress_bar, divide_into_chunks
from app import app

db.app = app
db.init_app(app)


def auth():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    if os.path.isfile("keys"):
        token = pickle.load(open("keys", "rb"))
        auth.set_access_token(token[0], token[1])
    else:
        try:
            redirect_url = auth.get_authorization_url()
        except tweepy.TweepError:
            print("Error! Failed to get request token.")

        print("visit to authorize with twitter: ", redirect_url)
        verifier = input("paste the verification code here: ")
        try:
            token = auth.get_access_token(verifier)
        except tweepy.TweepError:
            print("Error! Failed to get access token.")
        # save token in keys file
        pickle.dump(token, open("keys", "wb"))
    return auth


api = tweepy.API(auth())
print("Logged in as: " + api.me().screen_name)


def rate_limit_handler(cursor):
    while True:
        try:
            yield cursor.next()
        except tweepy.RateLimitError:
            print("Oh no!! We hit the rate limit. Resuming in 15 mins.")
            time.sleep(15 * 60)


def fetch_followers():
    user_keys = [
        "id_str",
        "name",
        "screen_name",
        "location",
        "description",
        "followers_count",
        "friends_count",
        "listed_count",
        "created_at",
        "favourites_count",
        "verified",
        "statuses_count",
    ]
    total_followers = api.me().followers_count
    print("Fetching {} followers".format(total_followers))
    db.drop_all()
    db.create_all()
    follower_ids = []
    print("Fetching follower ids!")
    for id in rate_limit_handler(tweepy.Cursor(api.followers_ids, count=5000).items()):
        follower_ids.append(id)
    print("Fetching user objects from ids!")
    for list_of_100 in list(divide_into_chunks(follower_ids, 100)):
        for i, user in enumerate(api.lookup_users(user_ids=list_of_100)):
            user_dict = dict((k, user.__dict__[k]) for k in user_keys)
            db.session.add(User(**user_dict))
            db.session.commit()
            print_progress_bar(
                i + 1,
                total_followers,
                prefix="Fetching {}/{} Followers".format(i + 1, total_followers),
                suffix="Fetched",
            )
    print("Done!")


def send_message(user_id, message):
    api.send_direct_message(user_id, message)


def mass_dm_followers(message, dry_run=True):
    followers = db.session.query(User.id_str, User.screen_name).all()
    total_followers = len(followers)
    print()
    if dry_run:
        print("Dry run is ON. Messages are not actually being sent. Phew")
    print("Sending message to {} followers".format(total_followers), end="\n\n")
    for i, (id, name) in enumerate(followers):
        print("\033[FSending DM to {}".format(name))
        print_progress_bar(i + 1, total_followers, suffix="Sent")
        if dry_run:
            time.sleep(0.01)
        # else:
        #     send_message(id, message) # DONT UNCOMMENT UNLESS U REALLY KNOW WHAT UR DOIN


def logout():
    if os.path.isfile("keys"):
        os.remove("keys")
        print("Logged out!")
    else:
        print("You aren't logged in.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mass DM tool for Twitter to convert followers to another platform",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "action",
        choices=["send", "fetch", "logout"],
        help="What do you wanna do?\n  - fetch - fetch followers\n  - send - send mass DM to followers\n  - logout - delete stored keys",
    )
    parser.add_argument("-m", "--message", help="Message to mass DM")
    parser.add_argument(
        "-dry", action="store_true", help="Don't actually send DMs. Just pretend."
    )
    args = parser.parse_args()
    if args.action == "fetch":
        if os.path.isfile("followers.sqlite"):
            refetch = input(
                "You've already fetched your followers. Are you sure you want to refetch them? This could take a while. [y/n]: "
            )
            if refetch == "y":
                fetch_followers()
            else:
                bye()
        else:
            fetch_followers()
    elif args.action == "send":
        if args.message:
            message = args.message
        else:
            message = input("What do you wanna say? Type your message below:\n")
        confirmed = input(
            "Here is your message one more time:\n\n{}\n\nAre you sure you want to send this? [y/n]: ".format(
                message
            )
        )
        if confirmed != "y":
            bye()
        if args.dry:
            mass_dm_followers(message, dry_run=True)
        else:
            send = input(
                "Dry run is not set. Are you sure you want to initiate the mass DM?? [y/n]: "
            )
            if send == "y":
                mass_dm_followers(message, dry_run=True)
            else:
                bye()
    elif args.action == "logout":
        logout()
