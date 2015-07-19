import binascii
import copy
import hashlib
import hmac
import json
import time

from . import exceptions

class Request:
	def __init__(self, app, method, path, query, body, cookies, wsgi_environ):
		self.app = app
		self.method = method
		self.path = path
		self.query = query
		self.body = body
		self.cookies = cookies
		self.wsgi_environ = wsgi_environ

	def get_secure_cookie(self, key, max_time):
		try:
			cookie = self.cookies[key].value
		except KeyError:
			return None
		try:
			value, ts, signature = cookie.split('|', 3)
			ts = int(ts)
		except ValueError:
			raise exceptions.HTTPException(400, 'invalid %s cookie: %s' % (key, cookie))
		value_ts = '%s|%s' % (value, int(ts))
		if hmac.compare_digest(signature, _hash(value_ts, self.app.cookie_secret)):
			if max_time is not None and ts + max_time.total_seconds() < time.time(): # cookie has expired
				return None
			return value
		else:
			return None

class Response:
	BASE_HEADERS = [
		('Access-Control-Allow-Origin', '*'),
		('Access-Control-Allow-Headers', 'Authorization, X-Requested-With, X-Request'),
	]
	DEFAULT_HEADERS = BASE_HEADERS
	ERROR_HEADERS = BASE_HEADERS + [('Content-type', 'text/plain')]

	json_encoder = json.JSONEncoder(indent='\t')

	def __init__(self, body=None, code=200, content_type='text/plain', location=None):
		self.body = body
		self.code = code

		headers = copy.copy(self.DEFAULT_HEADERS)
		headers.append(('Content-Type', content_type))
		if location:
			headers.append(('Location', location))
		self.headers = headers

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
			cookie += '; Max-Age=%d' % max_age.total_seconds()
		if secure:
			cookie += '; Secure'
		if http_only:
			cookie += '; HttpOnly'
		self.headers.append(('Set-Cookie', cookie))

	def set_secure_cookie(self, request, key, value, **kwargs):
		ts = int(time.time())
		value_ts = '%s|%s' % (value, ts)
		signature = _hash(value_ts, request.app.cookie_secret)
		value_signed = '%s|%s' % (value_ts, signature)
		self.set_cookie(key, value_signed, **kwargs)

	@classmethod
	def json(cls, obj):
		body = cls._gen_json(obj)
		return Response(body, content_type='application/json')

	@classmethod
	def _gen_json(cls, obj):
		for chunk in cls.json_encoder.iterencode(obj):
			yield chunk.encode('utf-8')

	@classmethod
	def render(cls, request, template, context):
		body = request.app.template_engine.render(template, context)
		response = cls(body, content_type='text/html')
		return response

def _hash(value_ts, cookie_secret):
	dk = hashlib.pbkdf2_hmac('sha256', value_ts.encode(), cookie_secret, 100000)
	signature = binascii.hexlify(dk)
	return signature.decode()
