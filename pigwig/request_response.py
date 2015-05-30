import copy

class Request:
	def __init__(self, app, query):
		self.app = app
		self.query = query

class Response:
	BASE_HEADERS = [
		('Access-Control-Allow-Origin', '*'),
		('Access-Control-Allow-Headers', 'Authorization, X-Requested-With, X-Request'),
	]
	DEFAULT_HEADERS = BASE_HEADERS
	ERROR_HEADERS = BASE_HEADERS + [('Content-type', 'text/plain')]

	def __init__(self, body, content_type='text/plain'):
		self.body = body
		self.content_type = content_type
		self.headers = copy.copy(self.DEFAULT_HEADERS)
		self.headers.append(('Content-Type', self.content_type))

	def set_cookie(self, key, value, domain=None, path=None, expires=None, max_age=None, secure=False, http_only=False):
		cookie = '%s=%s' % (key, value)
		if domain:
			cookie += '; Domain=%s' % domain
		if path:
			cookie += '; Path=%s' % path
		if expires:
			expires = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
			cookie += '; Expires=%s' % expires
		if max_age:
			cookie += '; Max-Age=%d' % max_age
		if secure:
			cookie += '; Secure'
		if http_only:
			cookie += '; HttpOnly'
		self.headers.append(('Set-Cookie', cookie))

	@classmethod
	def render(cls, request, template, context):
		body = request.app.template_engine.render(template, context)
		response = cls(body, content_type='text/html')
		return response
