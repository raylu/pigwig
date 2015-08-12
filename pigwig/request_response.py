import binascii
import copy
import hashlib
import hmac
import json
import time

from . import exceptions

class Request:
	'''
	an instance of this class is passed to every route handler. has the following instance attrs:

	* ``app`` - an instance of :class:`.PigWig`
	* ``method`` - the request method/verb (``GET``, ``POST``, etc.)
	* ``path`` - WSGI environ ``PATH_INFO`` (``/foo/bar``)
	* ``query`` - dict of parsed query string. duplicate keys appear as lists
	* ``body`` - dict of parsed body content. see :attr:`PigWig.content_handlers` for a list
	  of supported content types
	* ``cookies`` - an instance of
	  `http.cookies.SimpleCookie <https://docs.python.org/3/library/http.cookies.html#http.cookies.SimpleCookie>`_
	* ``wsgi_environ`` - the raw `WSGI environ <https://www.python.org/dev/peps/pep-0333/#environ-variables>`_
	  handed down from the server
	'''

	def __init__(self, app, method, path, query, body, cookies, wsgi_environ):
		self.app = app
		self.method = method
		self.path = path
		self.query = query
		self.body = body
		self.cookies = cookies
		self.wsgi_environ = wsgi_environ

	def get_secure_cookie(self, key, max_time):
		'''
		decode and verify a cookie set with :func:`Response.set_secure_cookie`

		:param key: ``key`` passed to ``set_secure_cookie``
		:type max_time: `datetime.timedelta <https://docs.python.org/3/library/datetime.html#timedelta-objects>`_
		:param max_time: amount of time since cookie was set that it should be considered valid for.
		  this is normally equal to the ``max_age`` passed to ``set_secure_cookie``. longer times mean
		  larger windows during which a replay attack is valid.
		:rtype: str or None
		'''
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
	'''
	every route handler should return an instance of this class (or raise an :class:`.exceptions.HTTPException`)

	:param body: if ``None``, the response body is empty.
	  if a ``str``, the response body is UTF-8 encoded.
	  if a generator, the response streams the yielded bytes.
	:param code: HTTP status code; the "reason phrase" is generated automatically from
	  `http.client.responses <https://docs.python.org/3/library/http.client.html#http.client.responses>`_
	:param content_type: sets the Content-Type header
	:param location: if not ``None``, sets the Location header
	'''

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
		'''
		adds a Set-Cookie header

		:type expires: datetime.datetime
		:param expires: if set to a value in the past, the cookie is deleted. if this and ``max_age`` are
		  not set, the cookie becomes a session cookie.
		:type max_age: datetime.timedelta
		:param max_age: according to the spec, has precedence over expires. if you specify both, both are sent.
		:param secure: controls when the browser sends the cookie back - unrelated to :func:`set_secure_cookie`

		see `the docs <https://tools.ietf.org/html/rfc6265#section-4.1>`_ for an explanation of the other params
		'''
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
		'''
		this function accepts the same keyword arguments as :func:`.set_cookie` but stores a
		timestamp and a signature based on ``request.app.cookie_secret``. decode with
		:func:`Request.get_secure_cookie`.

		the signature is a SHA-256
		`hashlib.pbkdf2_hmac <https://docs.python.org/3/library/hashlib.html#hashlib.pbkdf2_hmac>`_
		of the value and the timestamp at 100,000 rounds. the value is *not* encrypted and is
		readable by the user, but is signed and tamper-proof (assuming the ``cookie_secret`` is
		secure). because we store the signing time, expiry is checked with ``get_secure_cookie``.
		you generally will want to pass this function a ``max_age`` equal to ``max_time`` used when
		reading the cookie.
		'''
		ts = int(time.time())
		value_ts = '%s|%s' % (value, ts)
		signature = _hash(value_ts, request.app.cookie_secret)
		value_signed = '%s|%s' % (value_ts, signature)
		self.set_cookie(key, value_signed, **kwargs)

	@classmethod
	def json(cls, obj):
		'''
		generate a streaming :class:`.Response` object from an object with an ``application/json``
		content type. the default :attr:`.json_encoder` indents with tabs - override if you want
		different indentation or need special encoding.
		'''
		body = cls._gen_json(obj)
		return Response(body, content_type='application/json')

	@classmethod
	def _gen_json(cls, obj):
		'''
		internal use generator for converting
		`json.JSONEncoder.iterencode <https://docs.python.org/3/library/json.html#json.JSONEncoder.iterencode>`_
		output to bytes
		'''
		for chunk in cls.json_encoder.iterencode(obj):
			yield chunk.encode('utf-8')

	@classmethod
	def render(cls, request, template, context):
		'''
		generate a streaming :class:`.Response` object from a template and a context with a
		``text/html`` content type.

		:type request: :class:`.Request`
		:param request: the request to generate the response for
		:type template: str
		:param template: the template name to render, relative to ``request.app.template_dir``
		:param context: if you used the default jinja2 template engine, this is a dict

		'''
		body = request.app.template_engine.stream(template, context)
		response = cls(body, content_type='text/html')
		return response

def _hash(value_ts, cookie_secret):
	dk = hashlib.pbkdf2_hmac('sha256', value_ts.encode(), cookie_secret, 100000)
	signature = binascii.hexlify(dk)
	return signature.decode()
