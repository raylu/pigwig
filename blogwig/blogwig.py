#!/usr/bin/env python3

import binascii
import datetime
import functools
import getpass
import hashlib
import hmac
import os
import sqlite3
from os import path

from pigwig import PigWig, Response, default_http_exception_handler
from pigwig.exceptions import HTTPException

blogwig_dir = path.normpath(path.dirname(path.abspath(__file__)))
template_dir = path.join(blogwig_dir, 'templates')
db_path = path.join(blogwig_dir, 'blogwig.db')
db = sqlite3.connect(db_path)
db.row_factory = sqlite3.Row

LOGIN_TIME = datetime.timedelta(days=30)

def routes():
	return [
		('GET', '/', root),
		('GET', '/post/<id>', post),
		('GET', '/posts/<path:ids>', posts),
		('GET', '/login', login_form),
		('POST', '/login', login),
		('GET', '/admin', admin),
		('POST', '/admin/post', admin_post),
	]

def root(request):
	posts = db.execute('''
		SELECT posts.id, users.username, posts.title, posts.body
		FROM posts JOIN users on posts.user_id = users.id
		ORDER BY posts.id DESC LIMIT 10
	''')

	logged_in = False
	if request.get_secure_cookie('user_id', LOGIN_TIME):
		logged_in = True

	return Response.render(request, 'root.jinja2', {'posts': posts, 'logged_in': logged_in})

def post(request, id):
	posts = db.execute('''
		SELECT users.username, posts.title, posts.body
		FROM posts JOIN users on posts.user_id = users.id
		WHERE posts.id = ?
	''', id)
	try:
		post = next(posts)
	except StopIteration:
		raise HTTPException(404, 'invalid post id')
	return Response.render(request, 'posts.jinja2', {'posts': [post]})

def posts(request, ids):
	ids = list(map(int, ids.split('/')))
	posts = db.execute('''
		SELECT users.username, posts.title, posts.body
		FROM posts JOIN users on posts.user_id = users.id
		WHERE posts.id IN (%s)
	''' % ','.join('?' * len(ids)), ids)
	return Response.render(request, 'posts.jinja2', {'posts': posts})

def login_form(request):
	return Response.render(request, 'login.jinja2', {})

def login(request):
	try:
		username = request.body['username']
		password = request.body['password']
	except KeyError:
		raise HTTPException(400, 'username or password missing')
	cur = db.execute('SELECT id, password, salt FROM users WHERE username = ?', (username,))
	user = next(cur)
	hashed = _hash(password, user['salt'])
	if hmac.compare_digest(user['password'], hashed):
		response = Response(code=303, location='/admin')
		response.set_secure_cookie(request, 'user_id', str(user['id']), max_age=LOGIN_TIME)
		return response
	else:
		raise HTTPException(401, 'incorrect username or password')

def authed(f):
	@functools.wraps(f)
	def wrapper(request):
		user_id = request.get_secure_cookie('user_id', LOGIN_TIME)
		if not user_id:
			return Response(code=303, location='/login')
		return f(request, user_id)
	return wrapper

@authed
def admin(request, user_id):
	return Response.render(request, 'admin.jinja2', {})

@authed
def admin_post(request, user_id):
	try:
		title = request.body['title']
		body = request.body['body']
	except KeyError:
		raise HTTPException(400, 'title or body missing')
	with db:
		db.execute('INSERT INTO posts (user_id, title, body) VALUES(?, ?, ?)', (user_id, title, body))
	return Response(code=303, location='/admin')

def http_exception_handler(e, errors, request, app):
	if e.code == 404:
		return Response.render(request, '404.jinja2', {})
	return default_http_exception_handler(e, errors, request, app)

def init_db():
	print('creating blogwig.db')
	with db:
		db.executescript('''
			CREATE TABLE IF NOT EXISTS users (
				id INTEGER PRIMARY KEY,
				username TEXT NOT NULL UNIQUE,
				password TEXT NOT NULL,
				salt BLOB NOT NULL
			);
			CREATE TABLE IF NOT EXISTS posts (
				id INTEGER PRIMARY KEY,
				user_id INTEGER NOT NULL,
				title TEXT NOT NULL UNIQUE,
				body TEXT NOT NULL,
				FOREIGN KEY(user_id) REFERENCES users(id)
			);
		''')
		print('time to create your blogwig user!')
		username = input('username: ')
		password = getpass.getpass('password: ')
		create_user(username, password)

def create_user(username, password):
	salt = os.urandom(16)
	hashed = _hash(password, salt)
	db.execute('INSERT INTO users (username, password, salt) VALUES(?, ?, ?)',
			(username, hashed, salt))

def _hash(password, salt):
	dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
	return binascii.hexlify(dk)

app = PigWig(routes, template_dir=template_dir, cookie_secret=b'this is super secret',
		http_exception_handler=http_exception_handler)

def main():
	try:
		cur = db.execute('SELECT id FROM users LIMIT 1')
	except sqlite3.OperationalError: # table doesn't exist
		init_db()
		cur = db.execute('SELECT id FROM users LIMIT 1')
	if not cur.fetchone():
		init_db()
	app.main()

if __name__ == '__main__':
	main()
