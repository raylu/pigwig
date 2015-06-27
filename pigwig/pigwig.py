import copy
import re
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
from .templates_jinja import JinjaTemplateEngine

class RouteDict(dict):
	def __setitem__(self, key, value):
		if key in self:
			raise exceptions.RouteConflict()
		else:
			super().__setitem__(key, value)

class RouteTree(RouteDict):
	def __init__(self, routes):
		for method, path, handler in routes:
			path_elements = path[1:].split('/')
			node = self
			for element in path_elements:
				param = re.match('<(\w+)>', element)
				if param:
					node['param'] = RouteDict()
					node = node['param']
					node['name'] = param.group(1)
					node['methods'] = RouteDict()
					continue
				if element not in node:
					node[element] = RouteDict()
					node[element]['methods'] = RouteDict()
				node = node[element]
			node['methods'][method] = handler

	def get_handler(self, method, path):
		path_elements = path[1:].split('/')
		node = self
		kwargs = {}
		for element in path_elements:
			node_exists = node.get(element)
			if not node_exists:
				try:
					node = node['param']
				except KeyError:
					raise exceptions.HTTPException(404, 'Route %s not found' % path)
				key = node['name']
				kwargs[key] = element
			else:
				node = node[element]
		try:
			handler = node['methods'][method]
		except KeyError:
			raise exceptions.HTTPException(405, 'Method %s not allowed' % method)
		return handler, kwargs

class PigWig:
	def __init__(self, routes, template_dir=None, template_engine=JinjaTemplateEngine, cookie_secret=None):
		if callable(routes):
			routes = routes()
		self.routes = RouteTree(routes)

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

			handler, kwargs = self.routes.get_handler(request.method, request.path)
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
