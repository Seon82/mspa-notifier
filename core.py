import requests
from lxml import html
import psutil
import feedparser
import time


def getFirstOfBatch(feed):
    entries = feed['entries']
    latest_time = time.mktime(entries[0]['published_parsed'])
    for i, entry in enumerate(entries):
        if latest_time - time.mktime(entry['published_parsed']) >=60:
            return entries[i-1]


def getLatestRSS(link):
    feed = feedparser.parse(link)
    return getFirstOfBatch(feed)['link']


def getLatestLink(link, xpath):
    page = requests.get(link)
    tree = html.fromstring(page.content)
    tree.make_links_absolute(link)
    latest_link = tree.xpath(xpath)[0]
    return latest_link


def isSavingPower():
    '''Returns True iif thelaptop is unplugged and the battery below 20%'''
    battery = psutil.sensors_battery()
    if battery == None: # Home computer, no batteries
        return False
    plugged = battery.power_plugged
    percent = str(battery.percent)
    return (not plugged) or int(percent)<=20

