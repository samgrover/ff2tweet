#!/usr/bin/env python
#
# This tool takes some posts made to FriendFeed and converts it into a tweet for Twitter.

from friendfeed import *
from ConfigParser import ConfigParser
import re
import urllib2
import twitter
import sys

# Globals
TWITTER_USERNAME = ''
TWITTER_PASSWORD = ''
FRIENDFEED_USERNAME = ''
FRIENDFEED_REMOTEKEY = ''
BITLY_USERNAME = ''
BITLY_APIKEY = ''
BITLY_VERSION = ''
LAST_ENTRY_FILE = ''

# Constants
TWITTER_LIMIT_CHARS = 140
SOURCE_NAME = "ff2tweet"

def do_request(api_call):
    request = urllib2.Request(api_call)
    stream = urllib2.urlopen(request)
    response = stream.read()
    stream.close()
    return response

def shorten_url(link):
    if BITLY_USERNAME == '':
        api_call = "http://bit.ly/api?url=" + link
        url = do_request(api_call)
    else:
        api_call = "http://api.bit.ly/shorten?version=" + BITLY_VERSION \
                    + "&longUrl=" + link \
                    + "&login=" + BITLY_USERNAME \
                    + "&apiKey=" + BITLY_APIKEY
        response = do_request(api_call)
        op = parse_json(response)
        url = op["results"][link]["shortUrl"]
    return url

def post_tweet(tweet):
    tw_service = twitter.Twitter(TWITTER_USERNAME, TWITTER_PASSWORD)
    try:
        tw_service.statuses.update(status=tweet, source=SOURCE_NAME)
    except twitter.TwitterError:
        print "Error in posting: " + tweet
        return False
    return True


def format_tweet(ff_entry):
    # If posted to a room, just return None
    if ff_entry.has_key("room"):
        # print "Posted to a room"
        return None
    
    text = ff_entry["title"]
    ff_id = ff_entry["id"]
    link = ff_entry["link"]
    comments = ff_entry["comments"]
    media = ff_entry["media"]
    
    has_media = None
    outside_link = None
    
    # Check if first comment is from the user. If so, that becomes the tweet text instead of the title
    if len(comments) > 0:
        if comments[0]["user"]["nickname"] == FRIENDFEED_USERNAME:
            text = comments[0]["body"]
    
    # Check if media, like photo, is attached
    if len(media) > 0:
        link = media[0]["link"]
        has_media = True
    else:
        has_media = False
    
    # Check if the link is to an ff entry
    x = re.search(ff_id, link)
    if x is None:
        outside_link = True
    else:
        outside_link = False
    
    if has_media is False and outside_link is False:
        link = None
    
    # Shorten link
    tweet_len = 0
    url = ""
    if link is None:
        tweet_len = len(text)
    else:
        url = shorten_url(link)
        tweet_len = len(text) + len(url) + 1
    
    if tweet_len > TWITTER_LIMIT_CHARS:
        index = TWITTER_LIMIT_CHARS - len(url) - len("... ")
        text = text[:index]
        text = text + "... " + url
    else:
        text = text + " " + url
    
    return text


# Main
if __name__ == "__main__":
    # Import the config file
    config = ConfigParser()
    config.read("ff2tweet.ini")
    TWITTER_USERNAME = config.get("twitter", "username")
    TWITTER_PASSWORD = config.get("twitter", "password")
    FRIENDFEED_USERNAME = config.get("friendfeed", "username")
    FRIENDFEED_REMOTEKEY = config.get("friendfeed", "remotekey")
    BITLY_USERNAME = config.get("bitly", "username")
    BITLY_APIKEY = config.get("bitly", "api_key")
    BITLY_VERSION = config.get("bitly", "version")
    LAST_ENTRY_FILE = config.get("files", "last_entry")
    
    ff_service = FriendFeed()
    try:
        feed = ff_service.fetch_user_feed(FRIENDFEED_USERNAME)
    except Exception:
        sys.exit(0)
    
    # Pick the topmost post
    postable = None
    for entry in feed["entries"]:
        if entry["service"]["id"] == "internal" or entry["service"]["id"] == "googlereader":
            # postables.append(entry)
            postable = entry
            break

    # Compare against last entry posted with this script to ensure that this one is new
    if postable is not None:
        f = open(LAST_ENTRY_FILE, 'r')
        last_entry = f.read()
        f.close()
        exists = re.search(postable["id"], last_entry)
        if exists is None:
            tweet = format_tweet(postable)
            if tweet is not None:
                if post_tweet(tweet):
                    print "Tweeted: " + tweet
                    print len(tweet)
                    f = open(LAST_ENTRY_FILE, 'w')
                    last_entry = f.write(postable["id"])
                    f.close()

