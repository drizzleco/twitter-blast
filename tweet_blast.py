from secrets import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET
import tweepy
from models import User, db
from app import app
import time
import argparse
import os


db.app = app
db.init_app(app)


auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
# TODO: implement auth into app
# try:
#     redirect_url = auth.get_authorization_url()
# except tweepy.TweepError:
#     print("Error! Failed to get request token.")

# print("go to ", redirect_url)
# verifier = input("Verifier:")
# try:
#     token = auth.get_access_token(verifier)
#     print(token)
# except tweepy.TweepError:
#     print("Error! Failed to get access token.")
api = tweepy.API(auth)

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


def print_progress_bar(
    iteration,
    total,
    prefix="",
    suffix="",
    decimals=1,
    length=50,
    fill="█",
    print_end="\r",
):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + "-" * (length - filled_length)
    print("\r%s |%s| %s%% %s" % (prefix, bar, percent, suffix), end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()


def rate_limit_handler(cursor):
    while True:
        try:
            yield cursor.next()
        except tweepy.RateLimitError:
            print("Oh no!! We hit the rate limit. Resuming in 15 mins.")
            time.sleep(15 * 60)


def fetch_followers():
    total_followers = api.me().followers_count
    print("Fetching {} followers".format(total_followers))
    db.drop_all()
    db.create_all()
    for i, user in enumerate(rate_limit_handler(tweepy.Cursor(api.followers).items())):
        user_dict = dict((k, user.__dict__[k]) for k in user_keys)
        db.session.add(User(**user_dict))
        db.session.commit()
        print_progress_bar(
            i + 1,
            total_followers,
            prefix="Fetching {}/{} Followers".format(i + 1, total_followers),
            suffix="Fetched",
        )
    print("\nDone!")


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


def bye():
    print("Ok bye.")
    exit()


# send_message("1515209660", "test")

if __name__ == "__main__":
    # # get_followers()
    # mass_dm_followers("asdf")
    parser = argparse.ArgumentParser(
        description="Mass DM tool for Twitter to convert followers to another platform",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "action",
        choices=["send", "fetch"],
        help="What do you wanna do?\n  -'fetch' - fetch followers\n  -'send' - send mass DM to followers",
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
