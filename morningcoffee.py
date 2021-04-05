import requests
from flask import Flask
from flask import render_template, request, session
import datetime as dt
import feedparser
from urllib.parse import urlparse
from flask import request
import json
import os
from datetime import datetime
import hashlib
morningcoffee = Flask(__name__)


config = json.loads(os.environ.get('config'))
morningcoffee.secret_key = config["pinboard"]["secret_key"]

class Item:
    def __init__(self, id, url, title, description, time):
        self.id = id
        self.url = url
        self.title = title
        self.description = description
        # 2020-08-15T11:05:33Z
        self.time = datetime.strptime(time, '%Y-%m-%dT%H:%M:%SZ')

    def get_embed(self):
        # check for wordpress supported embeds
        wordpress_supported_embeds = ['www.instagram.com', 'www.youtube.com', 'vine.co', 'twitter.com']
        if self.get_domain() in wordpress_supported_embeds:
            return "\n\n" + self.url + "\n\n"

        # check for images
        extensions = ['.jpg', '.gif', '.png', '.bmp', '.jpeg']
        for e in extensions:
            if self.url.lower().endswith(e):
                return '<img src="' + self.url + '">'

        return None

    def get_description(self):
        if (self.description != None and self.description != ""):
            return "<blockquote>" + self.description + "</blockquote>"
        return ""

    def get_domain(self):
        o = urlparse(self.url)
        return o.hostname

def read_feed(url):
    d = feedparser.parse(url)
    return d.entries

def delicious_items():
    r = requests.get(session['config']['feed_url'])
    items = r.json()
    return items

def get_by_dt(dt, items):
    for i in items:
        if i.id == dt:
            return i
    return None

def md5(str):
    m = hashlib.md5()
    m.update(str.encode('utf-8-sig'))
    return m.hexdigest()

def wrap_into_items(delicious_items):
    items = []
    for fi in delicious_items:
        if ('feeds.del.icio.us' in session['config']['feed_url']):
            i = Item(fi['dt'], fi['u'], fi['d'], fi['n'])
        else:
            # i = Item(fi['hash'], fi['href'], fi['description'], fi['extended'], fi['time'])
            i = Item(md5(fi['u']), fi['u'], fi['d'], fi['n'], fi['dt'])
        items.append(i)
    return items;

@morningcoffee.route("/create-draft", methods=['POST'])
def create_draft():
    print("1")
    items = wrap_into_items(delicious_items())
    print("2")
    filtered_items = []
    selected = request.form.getlist('links')
    print("3")

    for s in selected:
        filtered_items.append(get_by_dt(s, items))
    print("4")
    html = render_template('items.html', items=filtered_items)
    print("5")
    today = dt.date.today()
    title = 'Morning Coffee - ' + today.strftime('%a, %b') + " " + today.strftime('%d').lstrip('0')
    post = {
        "content": html,
        "title": title,
        "status": "draft",
        "author": session['config']['wordpress']['author_id'],
        "categories": [session['config']['wordpress']['category_id']]
    }
    try:
        headers = {"user-agent": ""}
        post = requests.post(session['config']['wordpress']['url'] + "/wp-json/wp/v2/posts",
                             auth=(session['config']['wordpress']['username'],
                                   session['config']['wordpress']['password']),
                             headers=headers,
                             json=post).json()
    except Exception as e:
        print("Posting failed " + str(e))
    return render_template('result.html', post=post, url=session['config']['wordpress']['url'])
    

   

def get_current_user():
    # Just RR for now
    return "republic"

@morningcoffee.route("/")
def home():
    session['config'] = config[get_current_user()]
    items = wrap_into_items(delicious_items())
    return render_template('main.html', items=items)


if __name__ == "__main__":
        port = int(os.environ.get('PORT', 5000))
        morningcoffee.run(debug=True, host='0.0.0.0', port=port)


