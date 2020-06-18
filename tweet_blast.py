from secrets import CONSUMER_KEY, CONSUMER_SECRET
import tweepy, time, argparse, os, pickle, pydoc
from typing import List, Tuple
from models import User, db
from helpers import bye, print_progress_bar, divide_into_chunks, rate_limit_handler
from app import app

db.app = app
db.init_app(app)


def auth():
    """
    Reads in user keys if previously saved. If not saved, take user
    through Sign in with Twitter and serialize keys to a file.
    returns fully setup OAuthHandler 

    returns:
        tweepy.OAuthHandler - OAuthHandler to plug into tweepy.API call
    """
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    if os.path.isfile("keys"):
        token = pickle.load(open("keys", "rb"))
        auth.set_access_token(token[0], token[1])
    else:
        try:
            redirect_url = auth.get_authorization_url()
        except tweepy.TweepError:
            print("Error! Failed to get request token.")
        print("Visit to authorize with twitter: ", redirect_url)
        verifier = input("Paste the verification code here: ")
        try:
            token = auth.get_access_token(verifier)
        except tweepy.TweepError:
            print("Error! Failed to get access token.")
        pickle.dump(token, open("keys", "wb"))
    return auth


def fetch_followers():
    """
    Use tweepy to fetch user's followers' ids and then fetch their user objects
    and save to the db.
    """
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


def send_message(user_id: str, message: str):
    """
    Send message to user_id

    params:
        user_id(str) - user id of user as string
        message(str) - message to send
    """
    try:
        api.send_direct_message(user_id, message)
    except tweepy.RateLimitError:
        print("Oh no!! We hit the rate limit. Resuming tomorrow.")
        time.sleep(24 * 60 * 60)


def ranked_followers(rank_by: str, value: str) -> List[Tuple[str, str]]:
    """
    Rank followers based on specified criteria using db queries. Return a list
    of ranked followers' user id and their screen names who have not already
    been sent a DM.

    params:
        rank_by(str) - criteria to rank by
        value(str) - value to search for. only used for location 
                     and description filter
    """
    if rank_by == "recent":
        ranking = {"column": None}
    elif rank_by == "followers_count":
        ranking = {"column": User.followers_count}
    elif rank_by == "following_count":
        ranking = {"column": User.friends_count}
    elif rank_by == "listed_count":
        ranking = {"column": User.listed_count}
    elif rank_by == "favourites_count":
        ranking = {"column": User.favourites_count}
    elif rank_by == "statuses_count":
        ranking = {"column": User.statuses_count}
    elif rank_by == "location":
        ranking = {"location": value}
    elif rank_by == "description":
        ranking = {"description": value}
    else:
        raise Exception("No such ranking as " + rank_by)
    if "column" in ranking.keys():
        return (
            db.session.query(User.id_str, User.screen_name)
            .order_by(db.desc(**ranking))
            .filter_by(dm_sent=False)
            .all()
        )
    else:
        for key, value in ranking.items():
            return (
                db.session.query(User.id_str, User.screen_name)
                .filter(
                    getattr(User, key).like("%{}%".format(value)), User.dm_sent == False
                )
                .all()
            )


def mass_dm_followers(
    message: str, rank_by: str = "recent", value: str = "", dry_run: bool = True
):
    """
    Send mass DM to all followers in order of specificed ranking and set
    dm_sent flag for that user to True. Allows for dry run where messages
    are not actually sent out and dm_sent flag is not changed.

    params:
        message(str) - message to send out
        rank_by(str) - ranking method
        value(str) - value to search for. only used for location 
                     and description filter
        dry_run(bool) - set to True to only pretend to send messages
    """
    followers = ranked_followers(rank_by, value)
    total_followers = len(followers)
    if not total_followers:
        print(
            "No followers matched your criteria or they may have all been sent DMs already :("
        )
        bye()
    print()
    if dry_run:
        print("Dry run is ON. Messages are not actually being sent. Phew")
    print("Sending message to {} followers".format(total_followers), end="\n\n")
    for i, (id, name) in enumerate(followers):
        print("\033[FSending DM to {}".format(name))
        print_progress_bar(i + 1, total_followers, suffix="Sent")
        if dry_run:
            time.sleep(0.01)
        else:
            db.session.query(User).filter_by(id_str=id).update({"dm_sent": True})
            db.session.commit()
            # send_message(id, message) # DONT UNCOMMENT UNLESS U REALLY KNOW WHAT UR DOIN


def reset_dm_sent_flag():
    """
    Reset all followers dm_sent column to False
    """
    db.session.query(User).update({"dm_sent": False})
    db.session.commit()
    print("Followers DM sent flags reset!")


def logout():
    """
    Delete keys file
    """
    if os.path.isfile("keys"):
        os.remove("keys")
        print("Logged out!")
    else:
        print("You aren't logged in.")


if __name__ == "__main__":
    api = tweepy.API(auth())
    print("Logged in as: " + api.me().screen_name)
    # parser config
    parser = argparse.ArgumentParser(
        description="Mass DM tool for Twitter to convert followers to another platform",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "action",
        choices=["send", "fetch", "preview", "reset", "logout"],
        help="""
        What do you wanna do?
        - fetch - fetch followers
        - send - send mass DM to followers
        - preview - preview followers list ranking
        - reset - reset DM sent flags
        - logout - delete stored keys""",
    )
    parser.add_argument(
        "-dry", action="store_true", help="Don't actually send DMs. Just pretend."
    )
    args = parser.parse_args()

    # set ranking and value if action is preview or send
    if args.action == "preview" or args.action == "send":
        ranking_choices = [
            "recent",
            "followers_count",
            "following_count",
            "statuses_count",
            "listed_count",
            "favourites_count",
            "location",
            "description",
        ]
        value = ""
        print("Choose how you'd like to rank your followers:")
        for num, choice in enumerate(ranking_choices):
            print("{}) {}".format(str(num + 1), choice))
        ranking = ranking_choices[int(input("Enter the number of your choice: ")) - 1]
        if ranking == "location" or ranking == "description":
            value = input("Enter what you want to look for in {}: ".format(ranking))

    # execute actions
    if args.action == "fetch":
        # fetch action
        if os.path.isfile("followers.sqlite"):
            refetch = input(
                "You've already fetched your followers. Are you sure you want to refetch them? This could take a while. [y/n]: "
            )
            if refetch is "y":
                fetch_followers()
            else:
                bye()
        else:
            fetch_followers()
    elif args.action == "preview":
        # preview action
        followers = "Order of followers to be DM'ed(ranked by {} {}). Followers whom a DM hasn't been sent are shown:\n".format(
            ranking, value
        )
        ranked_followers = ranked_followers(rank_by=ranking, value=value)
        if ranked_followers:
            for _, user in ranked_followers:
                followers += user + "\n"
        else:
            followers += "No followers matched your criteria or they may have all been sent DMs already :("
        pydoc.pager(followers)
    elif args.action == "send":
        # send action
        print("\nNOTE: you may want to preview your followers rankings before sending")
        message = input("What do you wanna say? Type your message below:\n")
        confirmed = input(
            "Here is your message one more time:\n\n{}\n\nAre you sure you want to send this? [y/n]: ".format(
                message
            )
        )
        if confirmed != "y":
            bye()
        if args.dry:
            mass_dm_followers(message, rank_by=ranking, value=value, dry_run=True)
        else:
            send = input(
                "Dry run is not set. Are you sure you want to initiate the mass DM?? [y/n]: "
            )
            if send == "y":
                mass_dm_followers(message, rank_by=ranking, value=value, dry_run=False)
            else:
                bye()
    elif args.action == "reset":
        reset_dm_sent_flag()
    elif args.action == "logout":
        # logout action
        logout()
