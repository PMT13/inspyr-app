-- Holds the username of board creator, board id, board name, list of the tags it has, the board data itself (<-- not sure how to store board so just using this for now)
DROP TABLE boards CASCADE;
DROP TABLE images;
DROP TABLE tags;

create table boards (
  board_id SERIAL PRIMARY KEY,
  board_name text,
  user_id TEXT NOT NULL,
  username TEXT,
  tags_list text[],
  thumbnail text
);

create table images (
  image_id SERIAL PRIMARY KEY,
  board_id integer REFERENCES boards(board_id) ON DELETE CASCADE,
  image_name text,
  data bytea,
  x integer,
  y integer,
  w integer,
  h integer
);

-- Holds tag id, the tag name, and the number of boards with that tag 
create table tags (
  tag_id SERIAL PRIMARY KEY,
  tag_name text,
  size integer
);

alter table boards add column thumbnail bytea;

-- Adding in new user
"insert into users (username) values (%s)",(username)

-- Adding in new tag
"insert into tags (tag_name,size) values (%s,1)",(tag_name)

-- Adding in new board, incomplete because still unsure how to store the board 
"insert into boards (username,board_id,board_name,tag_list) values (%s)",(username,board_id,board_name,tag_list)

-- Find boards with a keywords in searchbar (title)
"SELECT * FROM boards WHERE board_name LIKE %(%s)%",(keyword)

-- Find boards with all keywords
"SELECT (board_id) FROM boards WHERE board_name ILIKE ALL %s",pattern_array

-- Find boards with a keywords in searchbar (tags)
"SELECT * FROM tags WHERE tag_name LIKE %(%s)%",(keyword)

-- Find boards with a certain tag 
"SELECT * FROM boards WHERE %s = ANY (tags_list)",(search_tag)

-- Find boards with a set of tags 
"SELECT (board_id) FROM boards WHERE tags_list @> %s",(tags,)

-- Update the "size" of tags when a new board is created with an existing tag
"UPDATE tags SET size = size + 1 WHERE tag_name = %s",(tag_name)

-- Find boards from a specific user
"SELECT (board_id) FROM boards WHERE username = %s", (username,)

-- Add a new tag to a board and update that boards tags in the database 
"UPDATE boards SET tags_list[%s] = %s WHERE board_id = %s",(last_taglist_index,new_tag,board_id)

-- Select an image by id
"SELECT * FROM images WHERE image_id=%s", (img_id,)

-- Add a new image to a board
"INSERT INTO images (board_id, image_name, data) VALUES (%s, %s, %s);", (board_id, filename, stream)

-- Select all images from a particular board
"SELECT * FROM images WHERE board_id = %s", (board_id,)