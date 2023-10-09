import os
import db
from functools import wraps
import json
from os import environ as env
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv, find_dotenv
from flask import Flask, render_template, request, g, jsonify, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode

app = Flask(__name__)

@app.before_first_request
def initialize():
    db.setup()

app.secret_key = env['secret_key']
oauth = OAuth(app)

AUTH0_CLIENT_ID = env['client_id']
AUTH0_CLIENT_SECRET = env['client_secret']
AUTH0_DOMAIN = env['client_domain']

auth0 = oauth.register(
   'auth0',
   client_id=AUTH0_CLIENT_ID,
   client_secret=AUTH0_CLIENT_SECRET,
   api_base_url='https://' + AUTH0_DOMAIN,
   access_token_url='https://'+AUTH0_DOMAIN+'/oauth/token',
   authorize_url='https://'+AUTH0_DOMAIN+'/authorize',
   client_kwargs={
       'scope': 'openid profile email',
   },
)

def requires_auth(f):
 @wraps(f)
 def decorated(*args, **kwargs):
   if 'profile' not in session:
     return redirect('/login')
   return f(*args, **kwargs)

 return decorated

@app.route('/callback')     # This is where the user is redirected to after being authorized 
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/')

@app.route('/login')  # Login Page
def login():
    return auth0.authorize_redirect(redirect_uri=url_for('callback_handling', _external = True))

@app.route('/logout')   #logout should redirect to home page
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@app.route('/',methods=['GET'])    # Landing Page
def home():
    tags = db.get_tags()
    boards= db.get_boards_keyword(False,[],'true')
    board_thumbnails = []
    board_names = []
    for board in boards:
        board_thumbnails.append(db.get_thumbnail(board))
        board_names.append(db.get_board_info(board)[1])
    
    return render_template('main.html',tags=tags,boards=boards,board_names=board_names,board_thumbnails=board_thumbnails)

@app.route('/',methods=['POST'])                                     # Landing Page
def update_home():
    data = request.get_json()
    tags = data[0]['tags']
    keywords =data[0]['keywords']
    checkbox = data[0]['includeAll']
    matching_boards = []
    keyword_equal_tag = []
    if checkbox == 'false' and keywords == [] and tags == []:                # when no keywords or tags are given, show all
        matching_boards= db.get_boards_keyword(False,[],'true')
    else:
        for i in keywords:                                                   # account for when a tag was typed in for a keyword
            keyword_equal_tag.append(i)
        keyword_tag_boards = db.get_boards_tags(keyword_equal_tag,checkbox)  # checks to see if the board has the keyword as a tag (aside from it being in the title)
        keyword_boards= db.get_boards_keyword(True,keywords,checkbox)        # Search by board name 
        keyword_boards = list(set(keyword_boards + keyword_tag_boards))         
        tag_boards = db.get_boards_tags(tags,checkbox)                       # Search by tags 
        if checkbox == 'false':                                          
            matching_boards = list(set(keyword_boards + tag_boards))
        else:
            for board in keyword_boards:                                # if checkbox is checked, compare values in tag and keyword 
                if board in tag_boards:                                 #   board arrays to see what boards are in both
                    matching_boards.append(board)
    board_names = []
    board_thumbnails = []
    for board in matching_boards:
        board_thumbnails.append(db.get_thumbnail(board))
        board_names.append(db.get_board_info(board)[1])
    results = {'tags': tags,
                'boards': matching_boards,
                'board_names':board_names,
                'thumbnails':board_thumbnails}
    return jsonify(results)

@app.route('/editor/<int:board_id>',methods=['GET'])   # Board Editor Page
@requires_auth
def editor(board_id):
    return render_template('editor.html', board_id = board_id, image_ids = db.get_image_ids(board_id), thumbnail = db.get_thumbnail(board_id), board = db.get_board_info(board_id),
                        userinfo=session['profile'],
                        userinfo_pretty=json.dumps(session['jwt_payload'],indent=4))
                        
@requires_auth
@app.route('/editor/<int:board_id>',methods=['POST'])   # Board Editor Page
def editor_post(board_id):
    data = request.get_json()
    delete_new_images = []
    db.update_images(data["image_data"])
    # app.logger.info(data["image_data"])
    for i in data["deleted_images"]:
        image = data["deleted_images"][i]
        if "img" in image:
            image = image[3:]
            db.delete_image(image)
        else:
            image = image[3:]
            delete_new_images.append(image)
    for image_id in data["new_images"]:
        if str(image_id) not in delete_new_images:
            image = data["new_images"][image_id]
            db.post_image(image, board_id)
    return render_template('editor.html', board_id = board_id, image_ids = db.get_image_ids(board_id), thumbnail = db.get_thumbnail(board_id),board = db.get_board_info(board_id),
                        userinfo=session['profile'],
                        userinfo_pretty=json.dumps(session['jwt_payload'],indent=4))
  
@requires_auth
@app.route('/editor/delete-board',methods=['POST'])  # Board Editor Page
def editor_delete_board():
    if request.method == 'POST':
        board_id = request.form.get('delete_board')
        db.delete_board(board_id)
    return redirect(url_for('profile'))
  
@requires_auth
@app.route('/editor/saved',methods=['POST']) # Board Editor Page
def editor_save():
    if request.method == 'POST':
        data = request.get_json()
        thumbnail = data["thumbnail"]
        board_id = data["board_id"]
        tags = data['tags']
        title = data["title"]
        db.post_thumbnail(thumbnail, board_id)
        db.update_tags(tags, board_id)
        db.update_title(title,board_id)
    return redirect(url_for('editor', board_id = board_id))

@app.route('/thumbnail<int:board_id>',methods=['GET']) # Board Editor Page
def view_thumbnail(board_id):
    return db.get_thumbnail(board_id)

@app.route('/image/<int:image_id>')  # Image viewer
def view_image(image_id):
    image = db.get_image(image_id)
    if image == 0:
        return render_template('error.html')
    return db.get_image(image_id)

@app.route('/board/<int:board_id>',methods=['GET'])   # Board Viewing Page
def view_board(board_id):
    board = db.get_board_info(board_id)
    comments = db.getComments(board_id)
    board_name = db.get_board_info(board_id)[1]
    username = db.get_username(board_id)
    if 'profile' not in session:
        return render_template('view.html', board_id = board_id, image_ids = db.get_image_ids(board_id), thumbnail = db.get_thumbnail(board_id), board = board, username = username, comments=comments,userinfo=None)
    return render_template('view.html', board_id = board_id, image_ids = db.get_image_ids(board_id), thumbnail = db.get_thumbnail(board_id), board = board, username = username, comments=comments,userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))

@app.route('/board/<int:board_id>',methods=['POST'])   # Board Viewing Page
@requires_auth
def view_board_post(board_id):
    if request.method == "POST":
        data = request.get_json()
        id = db.addComment(data[0]['comment'],data[1]['user'],data[2]['profilePic'],data[3]['time'],board_id)
        results = {'processed': 'true',
                    'id': id}
        return jsonify(results)
    return render_template('view.html')

@app.route('/create', methods=['POST'])
@requires_auth
def create_board():
    id = -1
    if request.method == 'POST':
        id = db.add_board(session['profile']['user_id'], session['profile']['name'], request.form.get('board_name'))
    if id != -1:
        return redirect(url_for('editor', board_id=id))
    else:
        return render_template('404.html'), 404


@app.route('/profile', methods=['GET'])   # "My Boards" Page
@requires_auth
def profile():
    boards = db.get_user_boards(session['profile']['user_id'])
    return render_template('profile.html',
                           boards = boards,
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'],indent=4))