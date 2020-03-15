import requests
from lxml import html
import psutil
import feedparser

def getLatestRSS(link):
    feed = feedparser.parse(link)
    return feed['entries'][0]['link']


def getLatestLink(link, xpath):
    page = requests.get(link)
    tree = html.fromstring(page.content)
    tree.make_links_absolute(link)
    latest_link = tree.xpath(xpath)
    return latest_link

# https://www.deconreconstruction.com/
# (//a[@class='project__link']//@href)[1]


def isSavingPower():
    '''Returns True iif thelaptop is unplugged and the battery below 20%'''
    battery = psutil.sensors_battery()
    if battery == None: # Home computer, no batteries
        return False
    plugged = battery.power_plugged
    percent = str(battery.percent)
    return (not plugged) or int(percent)<=20