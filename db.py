from contextlib import contextmanager
import logging
import os
import io
import base64

from flask import current_app, g, send_file
from flask.globals import request

from werkzeug.utils import secure_filename

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor

import base64
import io, re
from werkzeug.datastructures import FileStorage

pool = None

def setup():
    global pool
    DATABASE_URL = os.environ['DATABASE_URL']
    current_app.logger.info(f"creating db connection pool")
    pool = ThreadedConnectionPool(1, 16, dsn=DATABASE_URL, sslmode='require')


@contextmanager
def get_db_connection():
    connection = None
    try:
        connection = pool.getconn()
        yield connection
    finally:
        pool.putconn(connection)


@contextmanager
def get_db_cursor(commit=False):
    with get_db_connection() as connection:
      cursor = connection.cursor(cursor_factory=DictCursor)
      # cursor = connection.cursor()
      try:
          yield cursor
          if commit:
              connection.commit()
      finally:
          cursor.close()

def get_tags():
    with get_db_cursor(commit=True) as cur:                         
        match_list = []
        cur.execute("SELECT tag_name FROM tags WHERE size != 0")
        data = cur.fetchall()
        for i in data:
            match_list.append(i[0])
    
        cur.execute("SELECT (tag_id) FROM tags WHERE size = 0")
        data = cur.fetchall()
        for j in data:
            cur.execute("DELETE FROM tags WHERE tag_id = %s",j)
        return match_list

def get_boards_keyword(searching_bool,keywords,includeAll):
    with get_db_cursor() as cur:
        board_list = []
        if(searching_bool == False):                            # if no current tags or keywords being used, display all
            cur.execute("SELECT (board_id) FROM boards;")
            all_boards = cur.fetchall()
            for i in all_boards:
                board_list.append(i[0])
        else:
            if includeAll == 'false':
                for keyword in keywords:                        # else find boards that match keywords given by user 
                    pattern_match = "%" + keyword + "%" 
                    cur.execute("SELECT (board_id) FROM boards WHERE board_name ILIKE %s",(pattern_match,))
                    board_results = cur.fetchall()
                    for j in board_results:
                        if j not in board_list:
                            board_list.append(j[0])
            else:                                               # if checkbox is checked, search for boards associated with all keywords
                pattern_matching_array = []
                for keyword in keywords:
                    pattern_matching_array.append('%' + keyword + '%')
                cur.execute("SELECT (board_id) FROM boards WHERE board_name ILIKE ALL (%s)",(pattern_matching_array,))
                board_results = cur.fetchall()
                for k in board_results:
                    if k not in board_list:
                        board_list.append(k[0])
        return board_list

def get_boards_tags(tags,includeAll):
    current_app.logger.info(tags)
    with get_db_cursor() as cur:
        match_list = []
        if includeAll == 'true':
            # SELECT all board_id FROM boards table WHERE all the tags in the tags_list of a board is found within the set of chosen user tags 
            cur.execute("SELECT (board_id) FROM boards WHERE tags_list @> %s",(tags,))
            matching_boards = cur.fetchall()
            for i in matching_boards:
                match_list.append(i[0])
        else:
            for j in tags:
                cur.execute("SELECT (board_id) FROM boards WHERE %s = ANY (tags_list);",(j,))
                matching_boards = cur.fetchall()
                for i in matching_boards:
                    if i[0] not in match_list:
                        match_list.append(i[0])
        return match_list


def get_user_boards(user_id):
    with get_db_cursor() as cur:
        cur.execute('SELECT * FROM boards WHERE user_id=%s', (user_id,))
        return cur.fetchall()

def add_board(user_id, username, name="Default"):
    with get_db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO boards (user_id, username, board_name,tags_list) VALUES (%s, %s, %s, %s) RETURNING board_id;", (user_id, username, name, []))
        board_id = cur.fetchone()
        return board_id

def delete_board(board_id):
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT (tags_list) FROM boards where board_id = %s;",(board_id,))
        tags = cur.fetchone()
        for tag in tags[0]:
            cur.execute("UPDATE tags SET size = size - 1 where tag_name = %s",(tag,))
            cur.execute("SELECT (size) FROM tags where tag_name = %s",(tag,))
            tag_size = cur.fetchone()
            if tag_size[0] == 0:
                cur.execute("DELETE from tags where tag_name = %s",(tag,))
        cur.execute("DELETE FROM boards WHERE board_id = %s;", (board_id,))

def update_tags(tags,board_id):
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT (tags_list) from boards where board_id=%s",(board_id,))
        tags_list = cur.fetchone() 
        for tag in tags:                    # new set of tags given to board
            cur.execute("SELECT (size) from tags where tag_name=%s",(tag,))
            tag_count = cur.fetchone()
            if(tag_count == None):          # add new tags to the tags table, tag_count == None means this tag doesn't exist yet
                cur.execute("INSERT into tags (tag_name,size) values (%s,%s)",(tag,1))
            else:                           # else if tag does exist and it wasn't already part of board's tag_list, increment tag size
                if tag not in tags_list[0]:
                    cur.execute("UPDATE tags SET size = %s where tag_name = %s",(tag_count[0] + 1,tag))
        for old_tag in tags_list[0]:        # check for changes in the set of tags the board was previously given
            cur.execute("SELECT (size) from tags where tag_name=%s",(old_tag,))                 
            old_tag_count = cur.fetchone()
            if old_tag not in tags:         # if tag was removed from the board's tag_list
                if old_tag_count[0] - 1 == 0:  
                    cur.execute("DELETE from tags where tag_name = %s",(old_tag,))                   # if tag size is 0 now, remove it from table completely else just decrement
                else:
                    cur.execute("UPDATE tags SET size = %s where tag_name = %s",(old_tag_count[0] - 1,old_tag))
        cur.execute("UPDATE boards SET tags_list = %s where board_id = %s",(tags,board_id))     # update the tags_list in boards table with new set of tags

def update_title(title,board_id):
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE boards SET board_name = %s where board_id = %s",(title,board_id))

##### IMAGES #####

def get_image(img_id):
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM images WHERE image_id=%s", (img_id,))
        image_row = cur.fetchone()
        if image_row == None:
            return 0
        stream = io.BytesIO(image_row["data"])
        temp_filename = "temp.jpg"
        return send_file(stream, as_attachment = False, attachment_filename=temp_filename)

def get_images(board_id):
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM images WHERE board_id = %s", (board_id,))

def update_images(json):
    with get_db_cursor(commit=True) as cur:
        for image_id in json.keys():
            image = json[image_id]
            cur.execute("UPDATE images SET x=%s, y=%s, w=%s, h=%s WHERE image_id = %s", (image["x"], image["y"], image["w"], image["h"], int(image_id)))

def get_image_ids(board_id):
    with get_db_cursor() as cur:
        cur.execute("SELECT image_id, x, y, w, h FROM images WHERE board_id = %s", (board_id,))
        return cur.fetchall()
        #return [r['image_id', 'x', 'y'] for r in cur]

def post_image(image_json, board_id):
    # json sends image as base64-encoded string
    data = image_json["file"]
    # this somehow cleans up the encoding (not sure what that really means)
    imgstr = re.search(r'base64,(.*)', data).group(1)
    decoded_data = base64.b64decode(imgstr)
    # this turns it into byte data
    file_data = io.BytesIO(decoded_data)
    # this converts it into a FileStorage object, which is how we received it in the old method (post each image)
    image = FileStorage(file_data, filename='screenshot.jpg', content_type='application/json')
    stream = image.read()

    filename = secure_filename(image_json["name"])
    x = image_json["x"]
    y = image_json["y"]
    w = image_json["w"]
    h = image_json["h"]

    with get_db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO images (board_id, image_name, data, x, y, w, h) VALUES (%s, %s, %s, %s, %s, %s, %s);", (board_id, filename, stream, x, y, w, h))

def delete_image(img_id):
    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM images WHERE image_id=%s", (img_id,))

def post_thumbnail(thumbnail, board_id):
    # store thumbnail as base64 data uri
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE boards SET thumbnail = %s WHERE board_id = %s;", (thumbnail, board_id,))

def get_thumbnail(board_id):
    with get_db_cursor() as cur:
        cur.execute("select thumbnail from boards where board_id=%s;", (board_id,))
        thumbnail_row = cur.fetchone()
        thumbnail = thumbnail_row["thumbnail"]
        return thumbnail

def get_board_info(board_id):
    with get_db_cursor() as cur:
        cur.execute("select * from boards where board_id=%s;", (board_id,))
        return cur.fetchone()

def getComments(board_id):
    with get_db_cursor() as cur:
        json_list = []
        cur.execute("select row_to_json(t) from (select (content,username,img,time) from comments where board_id=%s) t;",(board_id,))
        data = cur.fetchone()
        while data != None:
            json_list.append(data[0])
            data = cur.fetchone()
        return json_list 

def addComment(comment,user,pic,time,board_id):
    with get_db_cursor(True) as cur:
        cur.execute("insert into comments (content,username,img,time,board_id) values (%s,%s,%s,%s,%s);",(comment,user,pic,time,board_id))
        cur.execute("select max(id) from comments;")
        data = cur.fetchone()
        return data[0]

def get_username(board_id):
    with get_db_cursor() as cur:
        cur.execute("select username from boards where board_id=%s", (board_id,))
        username = cur.fetchone()["username"]
        return username
