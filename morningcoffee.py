import requests
from flask import Flask
from flask import render_template, request, session
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
from wordpress_xmlrpc.methods import posts, taxonomies, users
import datetime
import feedparser
import hashlib
from urlparse import urlparse
from flask import request
import base64
import json

morningcoffee = Flask(__name__)
morningcoffee.secret_key = "secretkey"
config = {
    'republic': {
        'feed_url':'https://raptorsrepublic:password@api.pinboard.in/v1/posts/all?format=json&results=30&tag=RR',
        'wordpress': {
            'url': 'http://www.raptorsrepublic.com',
            'username': 'Arsenalist',
            'password': 'password',
            'category_id': 978,
            'author_id': 3
        }
    },
     'bluejays': {
        'feed_url': 'https://raptorsrepublic:password@api.pinboard.in/v1/posts/all?format=json&results=30&tag=BR',
        'wordpress': {
            'url': 'http://www.bluejaysrepublic.com',
            'username': 'Arsenalist',
            'password': 'password',
            'category_id': 4,
            'author_id': 2
        }
    },
      'tfc': {
        'feed_url': 'https://raptorsrepublic:password@api.pinboard.in/v1/posts/all?format=json&results=30&tag=TFC',
        'wordpress': {
            'url': 'http://www.tfcrepublic.com',
            'username': 'Arsenalist',
            'password': 'password',
            'category_id': 2,
            'author_id': 2
        }
    }
}   


class Item:
    def __init__(self, id, url, title, description):
        self.id = id
        self.url = url
        self.title = title
        self.description = description

    def get_embed(self):
        o = urlparse(self.url)
        wordpress_supported_embeds = ['www.instagram.com', 'www.youtube.com', 'vine.co', 'twitter.com']
        if o.hostname in wordpress_supported_embeds:
            return "\n\n" + self.url + "\n\n"
        return ""

    def get_description(self):
        if (self.description != None and self.description != ""):
            return "<blockquote>" + self.description + "</blockquote>"
        return ""


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

def wrap_into_items(delicious_items):
    items = []
    print "right here"
    for fi in delicious_items:
        if ('feeds.del.icio.us' in session['config']['feed_url']):
            i = Item(fi['dt'], fi['u'], fi['d'], fi['n'])
        else:
            i = Item(fi['hash'], fi['href'], fi['description'], fi['extended'])
        items.append(i)
    return items;

@morningcoffee.route("/create-draft", methods=['POST'])
def create_draft():
    items = wrap_into_items(delicious_items())
    filtered_items = []
    selected = request.form.getlist('links')
    for s in selected:
        filtered_items.append(get_by_dt(s, items))
    html = render_template('items.html', items=filtered_items)
    post = WordPressPost()
    today = datetime.date.today()
    post.title = 'Morning Coffee - ' + today.strftime('%a, %b') + " " + today.strftime('%d').lstrip('0')
    post.content = html.encode('utf-8')
    client = Client( session['config']['wordpress']['url'] + "/xmlrpc.php", session['config']['wordpress']['username'], session['config']['wordpress']['password'])

    category = client.call(taxonomies.GetTerm('category', session['config']['wordpress']['category_id']))
    post.terms.append(category)
    #user = client.call(users.GetUser(3))
    #print user
    post.user = session['config']['wordpress']['author_id']
    post.comment_status = 'open'
    post.id = client.call(posts.NewPost(post))
    return render_template('result.html', post=post, url=session['config']['wordpress']['url'])

   

def get_current_user():
    auth = request.headers.get('Authorization')
    if (auth is None):
        username = ""
    else:
        username = base64.b64decode(auth.split(" ")[1]).split(":")[0]
    return username

@morningcoffee.route("/")
def home():
    session['config'] = config[get_current_user()]
    #session['config'] = config['republic']
    items = wrap_into_items(delicious_items())
    return render_template('main.html', items=items)


if __name__ == "__main__":
        morningcoffee.run(debug=True)


