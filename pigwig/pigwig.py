import copy
import http.client
import http.cookies
from inspect import isgenerator
import json
import sys
import traceback
import urllib.parse
import wsgiref.simple_server

from . import exceptions, reloader
from .request_response import Request, Response
from .routes import build_route_tree
from .templates_jinja import JinjaTemplateEngine

class PigWig:
	'''
		main WSGI entrypoint. this is a class but defines a ``__call__`` so it can be passed
		directly to WSGI servers.

		has the following instance attrs:

		* ``routes`` - an internal representation of the route tree
		* ``template_engine`` - a class that takes a ``template_dir`` in the constructor and has a
		  ``.stream`` method that takes ``template_name, context`` as arguments (passed from user
		  code - for jinja2, context is a dictionary)
		* ``cookie_secret`` - app-wide secret used for signing secure cookies. see :func:`pigwig.Request.get_secure_cookie`
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

	def __call__(self, environ, start_response): # main WSGI entrypoint
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
				raise Exception(500, 'unhandled view response type: %s' % type(response.body))

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

		content_length = environ.get('CONTENT_LENGTH')
		if content_length:
			content_length = int(content_length)
		body = (environ['wsgi.input'], content_length)
		content_type = environ.get('CONTENT_TYPE')
		if content_type:
			handler = self.content_handlers.get(content_type)
			if handler:
				body = handler(environ['wsgi.input'], content_length)

		cookies = http.cookies.SimpleCookie()
		http_cookie = environ.get('HTTP_COOKIE')
		if http_cookie:
			cookies.load(http_cookie)

		return Request(self, method, path, query, body, cookies, environ)

	def main(self, host='0.0.0.0', port=8000):
		'''
		sets up the autoreloader and runs a
		`wsgiref.simple_server <https://docs.python.org/3/library/wsgiref.html#module-wsgiref.simple_server>`_.
		useful for development.
		'''
		reloader.init()
		if len(sys.argv) == 2:
			port = int(sys.argv[1])
		server = wsgiref.simple_server.make_server(host, port, self)
		print('listening on', port)
		server.serve_forever()

	@staticmethod
	def handle_urlencoded(body, length):
		return parse_qs(body.read(length).decode('utf-8'))

	@staticmethod
	def handle_json(body, length):
		return json.loads(body.read(length).decode('utf-8'))

PigWig.content_handlers = {
	'application/json': PigWig.handle_json,
	'application/x-www-form-urlencoded': PigWig.handle_urlencoded,
}

def parse_qs(qs):
	parsed = urllib.parse.parse_qs(qs, keep_blank_values=True, strict_parsing=True, errors='strict')
	for k, v in parsed.items():
		if len(v) == 1:
			parsed[k] = v[0]
	return parsed
