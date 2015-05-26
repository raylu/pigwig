import copy
import http.client
from inspect import isgenerator
import sys
import traceback
import urllib.parse
import wsgiref.simple_server

from .request_response import Request, Response
from .templates_jinja import JinjaTemplateEngine

class PigWig:
	BASE_HEADERS = [
		('Access-Control-Allow-Origin', '*'),
		('Access-Control-Allow-Headers', 'Authorization, X-Requested-With, X-Request'),
	]
	DEFAULT_HEADERS = BASE_HEADERS
	ERROR_HEADERS = BASE_HEADERS + [('Content-type', 'text/plain')]

	def __init__(self, routes, template_dir=None, template_engine=JinjaTemplateEngine):
		if callable(routes):
			routes = routes()
		self.routes = routes

		if template_dir:
			self.template_engine = template_engine(template_dir)
		else:
			self.template_engine = None

	def __call__(self, environ, start_response): # main WSGI entrypoint
		try:
			if environ['REQUEST_METHOD'] == 'OPTIONS':
				start_response('200 OK', copy.copy(self.DEFAULT_HEADERS))
				return []

			request = self.build_request(environ)

			handler = self.get_handler(environ['PATH_INFO'])
			response = handler(request)
			if not isinstance(response, Response):
				response = Response(response)
			if isinstance(response.body, str):
				response.body = [response.body.encode('utf-8')]
			elif not isgenerator(response.body):
				raise Exception(500, 'unhandled view response type: %s' % type(response.body))

			headers = copy.copy(self.DEFAULT_HEADERS)
			headers.append(('Content-Type', response.content_type))
			start_response('200 OK', headers)
			return response.body
		except HTTPException as e:
			response = '%d %s' % (e.code, http.client.responses[e.code])
			start_response(response, copy.copy(self.ERROR_HEADERS))
			return [e.body.encode('utf-8', 'replace')]
		except:
			tb = traceback.format_exc()
			start_response('500 Internal Server Error', copy.copy(self.ERROR_HEADERS))
			return [tb.encode('utf-8', 'replace')]

	def build_request(self, environ):
		qs = environ.get('QUERY_STRING')
		if qs:
			query = urllib.parse.parse_qs(qs, keep_blank_values=True, strict_parsing=True, errors='strict')
		else:
			query = {}
		return Request(self, query)

	def get_handler(self, path):
		path[1:].split('/')
		for route in self.routes:
			if route[0] == path:
				return route[1]
		raise HTTPException(404, 'unhandled path: ' + path)

	def main(self):
		port = 8000
		if len(sys.argv) == 2:
			port = int(sys.argv[1])
		server = wsgiref.simple_server.make_server('0.0.0.0', port, self)
		print('listening on', port)
		server.serve_forever()

class HTTPException(Exception):
	def __init__(self, code, body):
		self.code = code
		self.body = body
