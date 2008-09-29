#!/usr/bin/env python
#
# This tool takes some posts made to FriendFeed and converts it into a tweet for Twitter.
# Twitter API code is from http://mike.verdone.ca/twitter/
# FriendFeed API code is from http://code.google.com/p/friendfeed-api/

from friendfeed import *
import re
import urllib2
import twitter

# Enter the info below to customize
TWITTER_USERNAME = 'samgrover'
TWITTER_PASSWORD = ''
FRIENDFEED_USERNAME = 'samgrover'
FRIENDFEED_REMOTEKEY = ''

# Constants
TWITTER_LIMIT_CHARS = 140
LAST_ENTRY_FILE = "path to file that keeps track of last entry made"
SOURCE_NAME = "ff2tweet"

def shorten_url(link):
    api_call = "http://bit.ly/api?url=" + link
    request = urllib2.Request(api_call)
    stream = urllib2.urlopen(request)
    url = stream.read()
    stream.close()
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
    ff_service = FriendFeed()
    feed = ff_service.fetch_user_feed(FRIENDFEED_USERNAME)

    # Pick the topmost internal post
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

