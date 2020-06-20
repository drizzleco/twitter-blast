from secrets import CONSUMER_KEY, CONSUMER_SECRET
import tweepy, time, click, os, pickle, pydoc
from typing import List, Tuple
from models import User, Follower, db
from helpers import (
    RANK_BY,
    bye,
    print_progress_bar,
    divide_into_chunks,
    rate_limit_handler,
)

import app

follower_keys = [
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


def auth() -> tweepy.OAuthHandler:
    """
    Reads in user keys if previously saved. If not saved, take user
    through Sign in with Twitter and serialize keys to a file.
    returns fully setup OAuthHandler 

    returns:
        tweepy.OAuthHandler - OAuthHandler to plug into tweepy.API call
    """
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    if os.path.isfile(".keys"):
        token = pickle.load(open(".keys", "rb"))
        auth.set_access_token(token[0], token[1])
    else:
        try:
            redirect_url = auth.get_authorization_url()
        except tweepy.TweepError:
            print("Error! Failed to get request token.")
        print("Visit to authorize with twitter: ", redirect_url)
        verifier = input("Paste the verification code here: ")
        try:
            token = auth.get_access_token(verifier.strip())
        except tweepy.TweepError:
            print("Error! Failed to get access token.")
        pickle.dump(token, open(".keys", "wb"))
    return auth


def fetch_followers(username, api):
    """
    Use tweepy to fetch user's followers' ids and then fetch their user objects
    and save to the db.
    """
    total_followers = api.me().followers_count
    print("Fetching {} followers".format(total_followers))
    db.create_all()
    follower_ids = []
    print("Fetching follower ids!")
    for id in rate_limit_handler(tweepy.Cursor(api.followers_ids, count=5000).items()):
        follower_ids.append(id)
    print("Fetching user objects from ids!")
    for list_of_100 in list(divide_into_chunks(follower_ids, 100)):
        for i, user in enumerate(api.lookup_users(user_ids=list_of_100)):
            user_dict = dict((k, user.__dict__[k]) for k in follower_keys)
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
            user.followers.append(Follower(**user_dict))
            db.session.add(user)
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


def ranked_followers(username: str, rank_by: str, value: str) -> Follower:
    """
    Rank followers based on specified criteria using db queries. Return a list
    of ranked followers' user id and their screen names who have not already
    been sent a DM.

    params:
        username(str) - username of follower to rank for
        rank_by(str) - criteria to rank by
        value(str) - value to search for. only used for location 
                     and description filter
    """
    ranking = RANK_BY.get(rank_by, None)
    user = User.query.filter_by(username=username).first()
    followers_dm_not_sent = (
        db.session.query(Follower).filter_by(user_id=user.id, dm_sent=False).all()
    )
    if user.followers and not len(followers_dm_not_sent):
        raise Exception("DMs have been sent to all followers already :(")
    if ranking:
        return (
            db.session.query(Follower)
            .filter_by(user_id=user.id, dm_sent=False)
            .order_by(db.desc(**ranking))
            .all()
        )
    else:
        return (
            db.session.query(Follower)
            .filter(
                Follower.user_id == user.id,
                getattr(Follower, rank_by).like("%{}%".format(value)),
                Follower.dm_sent == False,
            )
            .all()
        )


def mass_dm_followers(
    username: str,
    message: str,
    rank_by: str = "recent",
    value: str = "",
    dry_run: bool = True,
):
    """
    Send mass DM to all followers in order of specificed ranking and set
    dm_sent flag for that user to True. Allows for dry run where messages
    are not actually sent out and dm_sent flag is not changed.

    params:
        username(str) - user of followers to DM
        message(str) - message to send out
        rank_by(str) - ranking method
        value(str) - value to search for. only used for location 
                     and description filter
        dry_run(bool) - set to True to only pretend to send messages
    """
    try:
        followers = ranked_followers(username, rank_by, value)
    except Exception as e:
        print(e)
        bye()
    total_followers = len(followers)
    if not total_followers:
        print("No followers matched your criteria :(")
        bye()
    print()
    if dry_run:
        print(
            "Dry run is ON. Messages are not actually being sent. Phew. Add the --real flag to send DMs"
        )
    print("Sending message to {} followers".format(total_followers), end="\n\n")
    for i, follower in enumerate(followers):
        print("\033[F\033[KSending DM to {}".format(follower.screen_name))
        print_progress_bar(i + 1, total_followers, suffix="Sent")
        if dry_run:
            time.sleep(0.01)
        else:
            db.session.query(Follower).filter_by(id_str=follower.id_str).update(
                {"dm_sent": True}
            )
            db.session.commit()
            # send_message(id, message) # DONT UNCOMMENT UNLESS U REALLY KNOW WHAT UR DOIN


# handlers
def prompt_ranking_value() -> Tuple[str, str]:
    """
    Prompt user for ranking choice and value if needed

    returns:
        ranking(str) - string value of ranking choice selected
        value(str) - string to search filter_by, if needed
    """
    value = ""
    print("Choose how you'd like to rank your followers:")
    for num, choice in enumerate(ranking_choices):
        print("{}) {}".format(str(num + 1), choice))
    ranking = ranking_choices[int(input("Enter the number of your choice: ")) - 1]
    if ranking == "location" or ranking == "description":
        value = input("Enter what you want to look for in {}: ".format(ranking))
    return ranking, value


def handle_fetch():
    """
    Fetch action
    """
    if os.path.isfile("tweet_blast.sqlite"):
        refetch = input(
            "You've already fetched your followers. Are you sure you want to refetch them? This could take a while. [y/n]: "
        )
        if refetch is "y":
            db.drop_all()
            db.create_all()
            fetch_followers(username, api)
        else:
            bye()
    else:
        fetch_followers(username, api)


def handle_preview():
    """
    Preview action
    """
    ranking, value = prompt_ranking_value()
    followers = "Order of followers to be DM'ed(ranked by {} {}). Followers whom a DM hasn't been sent are shown:\n".format(
        ranking, value
    )
    try:
        ranked = ranked_followers(username, rank_by=ranking, value=value)
        if ranked:
            for follower in ranked:
                followers += follower.screen_name + "\n"
        else:
            followers += "No followers matched your criteria :("
    except Exception as e:
        followers += str(e)
    pydoc.pager(followers)


def handle_send(real: bool):
    """
    Send action

    params:
        real(bool) - click real flag
    """
    ranking, value = prompt_ranking_value()
    print("\nNOTE: you may want to preview your followers rankings before sending")
    message = input("What do you wanna say? Type your message below:\n")
    confirmed = input(
        "Here is your message one more time:\n\n{}\n\nAre you sure you want to send this? [y/n]: ".format(
            message
        )
    )
    if confirmed != "y":
        bye()
    if real:
        send = input(
            "Dry run is not set. Are you sure you want to initiate the mass DM?? [y/n]: "
        )
        if send == "y":
            mass_dm_followers(
                username, message, rank_by=ranking, value=value, dry_run=False
            )
        else:
            bye()
    else:
        mass_dm_followers(username, message, rank_by=ranking, value=value, dry_run=True)


def handle_reset(username: str):
    """
    Reset all followers dm_sent column to False

    params:
        username(str) - user to reset follower flags for
    """
    user_id = User.query.filter_by(username=username).first().id
    db.session.query(Follower).filter_by(user_id=user_id).update({"dm_sent": False})
    db.session.commit()
    print("Followers DM sent flags reset!")


def handle_delete_keys():
    """
    Delete keys file
    """
    if os.path.isfile(".keys"):
        os.remove(".keys")
        print("Keys deleted!")
    else:
        print("You haven't been authorized yet.")


# parser config
@click.command()
@click.argument(
    "action", type=click.Choice(["send", "fetch", "preview", "reset", "delete_keys"]),
)
@click.option("--real", help="Actually send DMs.", is_flag=True)
def tweet_blast(action, real):
    """
    Mass DM tool for Twitter to convert followers to another platform
    """
    if action == "fetch":
        handle_fetch()
    elif action == "preview":
        handle_preview()
    elif action == "send":
        handle_send(real)
    elif action == "reset":
        handle_reset(username)
    elif action == "delete_keys":
        handle_delete_keys()


if __name__ == "__main__":
    api = tweepy.API(auth())
    username = api.me().screen_name
    print("Logged in as: " + username)
    tweet_blast()
