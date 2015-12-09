import cgi
import copy
import http.client
import http.cookies
from inspect import isgenerator
import json
import sys
import traceback
import urllib.parse
import wsgiref.simple_server

from . import exceptions
from .request_response import HTTPHeaders, Request, Response
from .routes import build_route_tree
from .templates_jinja import JinjaTemplateEngine

class PigWig:
	'''
		main WSGI entrypoint. this is a class but defines a :func:`.__call__` so instances of it can
		be passed directly to WSGI servers.

		:type routes: list or function
		:param routes: a list of 3-tuples: ``(method, path, handler)`` or a function that returns
		  such a list
		   * ``method`` is the HTTP method/verb (``GET``, ``POST``, etc.)
		   * ``path`` can either be a static path (``/foo/bar``) or have params (``/post/<id>``). params
		     are passed to the handler as keyword arguments. params cannot be optional, but you can map
		     two routes to a handler that takes an optional argument. params must make up the entire
		     path segment - you cannot have ``/post_<id>``.
		   * ``handler`` is a function taking a ``request`` positional argument and any number of param
		     keyword arguments
		  having two identical static routes or two overlapping param segments (``/foo/<bar>`` and
		  ``/foo/<baz>``) with the same method raises an :class:`.exceptions.RouteConflict`

		:type template_dir: str
		:param template_dir: if specified, a ``template_engine`` is created with this as the argument.
		  for ``pigwig.templates_jinja.JinjaTemplateEngine``, this should be an absolute path or it
		  will be relative to the current working directory.

		:param template_engine: a class that takes a ``template_dir`` in the constructor and has a
		  ``.stream`` method that takes ``template_name, context`` as arguments (passed from user
		  code - for jinja2, context is a dictionary)

		:type cookie_secret: str
		:param cookie_secret: app-wide secret used for signing secure cookies. see
		  :func:`Request.get_secure_cookie`

		has the following instance attrs:

		* ``routes`` - an internal representation of the route tree - not the list passed to the
		  constructor
		* ``template_engine``
		* ``cookie_secret``
	'''

	def __init__(self, routes, template_dir=None, template_engine=JinjaTemplateEngine, cookie_secret=None):
		if callable(routes):
			routes = routes()
		self.routes = build_route_tree(routes)

		if template_dir:
			self.template_engine = template_engine(template_dir)
		else:
			self.template_engine = None

		self.cookie_secret = cookie_secret

	def __call__(self, environ, start_response):
		''' main WSGI entrypoint '''
		try:
			if environ['REQUEST_METHOD'] == 'OPTIONS':
				start_response('200 OK', copy.copy(Response.DEFAULT_HEADERS))
				return []

			request = self.build_request(environ)

			handler, kwargs = self.routes.route(request.method, request.path)
			response = handler(request, **kwargs)
			if isinstance(response.body, str):
				response.body = [response.body.encode('utf-8')] # pylint: disable=no-member
			elif response.body is None:
				response.body = []
			elif not isgenerator(response.body):
				raise Exception('unhandled view response type: %s' % type(response.body))

			status_line = '%d %s' % (response.code, http.client.responses[response.code])
			start_response(status_line, response.headers)
			return response.body
		except exceptions.HTTPException as e:
			status_line = '%d %s' % (e.code, http.client.responses[e.code])
			start_response(status_line, copy.copy(Response.ERROR_HEADERS))
			return [e.body.encode('utf-8', 'replace')]
		except:
			tb = traceback.format_exc()
			sys.stderr.write(tb)
			start_response('500 Internal Server Error', copy.copy(Response.ERROR_HEADERS))
			return [tb.encode('utf-8', 'replace')]

	def build_request(self, environ):
		''' builds :class:`.Response` objects. for internal use. '''
		method = environ['REQUEST_METHOD']
		path = environ['PATH_INFO']

		qs = environ.get('QUERY_STRING')
		if qs:
			query = parse_qs(qs)
		else:
			query = {}

		headers = HTTPHeaders()

		content_length = environ.get('CONTENT_LENGTH')
		if content_length:
			headers['Content-Length'] = content_length
			content_length = int(content_length)
		body = (environ['wsgi.input'], content_length)
		content_type = environ.get('CONTENT_TYPE')
		if content_type:
			headers['Content-Type'] = content_type
			media_type, params = cgi.parse_header(content_type)
			handler = self.content_handlers.get(media_type)
			if handler:
				body = handler(environ['wsgi.input'], content_length, params)

		cookies = http.cookies.SimpleCookie()
		http_cookie = environ.get('HTTP_COOKIE')
		if http_cookie:
			cookies.load(http_cookie)

		for key in environ:
			if key.startswith('HTTP_'):
				headers[key[5:].replace('_', '-')] = environ[key]

		return Request(self, method, path, query, headers, body, cookies, environ)

	def main(self, host='0.0.0.0', port=8000):
		'''
		sets up the autoreloader and runs a
		`wsgiref.simple_server <https://docs.python.org/3/library/wsgiref.html#module-wsgiref.simple_server>`_.
		useful for development.
		'''

		have_reloader = True
		if sys.platform == 'linux':
			from . import reloader_linux as reloader
		elif sys.platform == 'darwin':
			try:
				from . import reloader_osx as reloader
			except ImportError as e:
				have_reloader = False
				print('install', e.name, 'for auto-reloading')
		else:
			have_reloader = False
			print('no reloader available for', sys.platform)
		if have_reloader:
			reloader.init()

		if len(sys.argv) == 2:
			port = int(sys.argv[1])
		server = wsgiref.simple_server.make_server(host, port, self)
		print('listening on', port)
		server.serve_forever()

	@staticmethod
	def handle_urlencoded(body, length, params):
		charset = params.get('charset', 'utf-8')
		return parse_qs(body.read(length).decode(charset))

	@staticmethod
	def handle_json(body, length, params):
		charset = params.get('charset', 'utf-8')
		return json.loads(body.read(length).decode(charset))

	@staticmethod
	def handle_multipart(body, length, params):
		params['boundary'] = params['boundary'].encode()
		form = cgi.parse_multipart(body, params)
		for k, v in form.items():
			if len(v) == 1:
				form[k] = v[0]
		return form

PigWig.content_handlers = {
	'application/json': PigWig.handle_json,
	'application/x-www-form-urlencoded': PigWig.handle_urlencoded,
	'multipart/form-data': PigWig.handle_multipart,
}

def parse_qs(qs):
	try:
		parsed = urllib.parse.parse_qs(qs, keep_blank_values=True, strict_parsing=True, errors='strict')
	except UnicodeDecodeError as e:
		qs_trunc = qs
		if len(qs_trunc) > 24:
			qs_trunc = qs_trunc[:24] + '...'
		raise exceptions.HTTPException(400, '%s\n%r' % (e, qs_trunc)) # "'utf-8' codec can't decode byte ..."
	except ValueError as e:
		raise exceptions.HTTPException(400, e.args[0]) # "bad query field: ..."
	for k, v in parsed.items():
		if len(v) == 1:
			parsed[k] = v[0]
	return parsed
