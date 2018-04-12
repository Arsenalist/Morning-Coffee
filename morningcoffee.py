import requests
from flask import Flask
from flask import render_template, request, session
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
from wordpress_xmlrpc.methods import posts, taxonomies, users
import datetime
import feedparser
import hashlib
from urllib.parse import urlparse
from flask import request
import base64
import json
import sys  
import os
import http.client
import xmlrpc.client

class RequestsTransport(xmlrpc.client.SafeTransport):
    """
    Drop in Transport for xmlrpclib that uses Requests instead of httplib
    """
    # change our user agent to reflect Requests
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36"

    def __init__(self, proxies=None, use_https=True, cert=None, verify=None, *args, **kwargs):
        self.proxies = kwargs.get("proxies")
        self.cert = cert
        self.verify = verify
        self.use_https = use_https
        self.proxies = proxies
        xmlrpc.client.SafeTransport.__init__(self, *args, **kwargs)

    def request(self, host, handler, request_body, verbose):
        """
        Make an xmlrpc request.
        """
        headers = {'User-Agent': self.user_agent}
        url = self._build_url(host, handler)
        try:
            resp = requests.post(url, data=request_body, headers=headers,
                                 stream=True,
                                 cert=self.cert, verify=self.verify, proxies=self.proxies)
        except ValueError:
            raise
        except Exception:
            raise  # something went wrong
        else:
            try:
                resp.raise_for_status()
            except requests.RequestException as e:
                raise xmlrpc.client.ProtocolError(url, resp.status_code,
                                              str(e), resp.headers)
            else:
                self.verbose = verbose
                return self.parse_response(resp.raw)

    def _build_url(self, host, handler):
        """
        Build a url for our request based on the host, handler and use_http
        property
        """
        scheme = 'https' if self.use_https else 'http'
        return '%s://%s/%s' % (scheme, host, handler)



morningcoffee = Flask(__name__)


config = None
if os.environ.get('config') is None:
    config_file = os.getcwd() + "/config.json"
    contents = open(config_file, "r").read()
    config = json.loads(contents)
else:
    config = json.loads(os.environ.get('config'))

morningcoffee.secret_key = config["pinboard"]["secret_key"]

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
    post.content = html

    transport = None
    if os.environ.get('FIXIE_URL'):
        proxies = {
            "http"  : os.environ.get('FIXIE_URL', ''),
            "https" : os.environ.get('FIXIE_URL', '')
        } 
        transport = RequestsTransport(proxies)        
 
    client = Client( session['config']['wordpress']['url'] + "/xmlrpc.php", session['config']['wordpress']['username'], session['config']['wordpress']['password'], 0, transport)
    category = client.call(taxonomies.GetTerm('category', session['config']['wordpress']['category_id']))
    post.terms.append(category)
    post.user = session['config']['wordpress']['author_id']
    post.comment_status = 'open'
    post.id = client.call(posts.NewPost(post))
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
        morningcoffee.run(debug=False, host='0.0.0.0', port=port)


