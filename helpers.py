from typing import List
import tweepy, time


def divide_into_chunks(l: List, n: int):
    """
    Split a list into chunks of n size

    params:
        l(list) - list to split up
        n(int) - size of sublists
    """
    for i in range(0, len(l), n):
        yield l[i : i + n]


def print_progress_bar(
    iteration: int,
    total: int,
    prefix: str = "",
    suffix: str = "",
    decimals: int = 1,
    length: int = 50,
    fill: str = "█",
    print_end: str = "\r",
):
    """
    Call in a loop to create terminal progress bar. Print new line on complete

    params:
        iteration(int) - current iteration 
        total(int) - total iterations 
        prefix(str) - prefix string 
        suffix(str) - suffix string 
        decimals(int) - positive number of decimals in percent complete 
        length(int) - character length of bar 
        fill(str) - bar fill character 
        print_end(str) - end character (e.g. "\r", "\r\n") 
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + "-" * (length - filled_length)
    print("\r%s |%s| %s%% %s" % (prefix, bar, percent, suffix), end=print_end)
    if iteration == total:
        print()


def rate_limit_handler(cursor: tweepy.Cursor):
    """
    Handler for tweepy Cursors and automatically stops
    execution when rate limit is reached

    params:
        cursor(tweepy.Cursor) - cursor to handle
    """
    while True:
        try:
            yield cursor.next()
        except tweepy.RateLimitError:
            print("Oh no!! We hit the rate limit. Resuming in 15 mins.")
            time.sleep(15 * 60)


def bye():
    """
    Stop execution of script.
    """
    print("Ok bye.")
    exit()
