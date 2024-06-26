from __future__ import annotations

import datetime
import hashlib
import hmac
import http.cookies
import json as jsonlib
import time
import typing
from collections import UserDict

from . import exceptions

if typing.TYPE_CHECKING:
	from .pigwig import PigWig

class Request:
	"""
	an instance of this class is passed to every route handler. has the following instance attrs:

	* ``app`` - an instance of :class:`.PigWig`
	* ``method`` - the request method/verb (``GET``, ``POST``, etc.)
	* ``path`` - WSGI environ ``PATH_INFO`` (``/foo/bar``)
	* ``query`` - dict of parsed query string. duplicate keys appear as lists
	* ``headers`` - :class:`.HTTPHeaders` of the headers
	* ``body`` - dict of parsed body content. see :attr:`PigWig.content_handlers` for a list
	  of supported content types
	* ``cookies`` - an instance of
	  `http.cookies.SimpleCookie <https://docs.python.org/3/library/http.cookies.html#http.cookies.SimpleCookie>`_
	* ``wsgi_environ`` - the raw `WSGI environ <https://www.python.org/dev/peps/pep-0333/#environ-variables>`_
	  handed down from the server
	"""

	def __init__(self, app: PigWig, method: str, path: str, query: typing.Mapping[str, str |  list[str]],
				headers: HTTPHeaders, body: dict, cookies: http.cookies.BaseCookie,
				wsgi_environ: dict[str, typing.Any]) -> None:
		self.app = app
		self.method = method
		self.path = path
		self.query = query
		self.headers = headers
		self.body = body
		self.cookies = cookies
		self.wsgi_environ = wsgi_environ

	def get_secure_cookie(self, key: str, max_time: datetime.timedelta) -> str | None:
		"""
		decode and verify a cookie set with :func:`Response.set_secure_cookie`

		:param key: ``key`` passed to ``set_secure_cookie``
		:type max_time: `datetime.timedelta <https://docs.python.org/3/library/datetime.html#timedelta-objects>`_
		  or None
		:param max_time: amount of time since cookie was set that it should be considered valid for.
		  this is normally equal to the ``max_age`` passed to ``set_secure_cookie``. longer times mean
		  larger windows during which a replay attack is valid. this can be None, in which case no
		  expiry check is performed
		:rtype: str or None
		"""
		assert self.app.cookie_secret is not None
		try:
			cookie = self.cookies[key].value
		except KeyError:
			return None
		try:
			value, ts_str, signature = cookie.rsplit('|', 2)
			ts_int = int(ts_str)
		except ValueError:
			raise exceptions.HTTPException(400, 'invalid %s cookie: %s' % (key, cookie))
		value_ts = '%s|%d' % (value, ts_int)
		if hmac.compare_digest(signature, _hash(key + '|' + value_ts, self.app.cookie_secret)):
			if max_time is not None and ts_int + max_time.total_seconds() < time.time(): # cookie has expired
				return None
			return value
		else:
			return None

class Response:
	'''
	every route handler should return an instance of this class (or raise an :class:`.exceptions.HTTPException`)

	:param body:
	  * if ``None``, the response body is empty
	  * if a ``str``, the response body is UTF-8 encoded
	  * if a ``bytes``, the response body is sent as-is
	  * if a generator, the response streams the yielded bytes
	:type code: int
	:param code: HTTP status code; the "reason phrase" is generated automatically from
	  `http.client.responses <https://docs.python.org/3/library/http.client.html#http.client.responses>`_
	:param content_type: sets the Content-Type header
	:param location: if not ``None``, sets the Location header. you must still specify a 3xx code
	:param extra_headers: if not ``None``, an iterable of extra header 2-tuples to be sent

	has the following instance attrs:

	* ``code``
	* ``body``
	* ``headers`` - a list of 2-tuples
	'''

	DEFAULT_HEADERS: typing.Sequence[tuple[str, str]] = (
		('Access-Control-Allow-Origin', '*'),
		('Access-Control-Allow-Headers', 'Authorization, X-Requested-With, X-Request'),
	)

	json_encoder = jsonlib.JSONEncoder(indent='\t')
	simple_cookie = http.cookies.SimpleCookie()

	def __init__(self, body: str | bytes | typing.Iterator[bytes] | None=None, code: int=200,
				content_type: str='text/plain', location: str | None=None,
				extra_headers: list[tuple[str, str]] | None=None) -> None:
		self.body = body
		self.code = code

		headers = list(self.DEFAULT_HEADERS)
		headers.append(('Content-Type', content_type))
		if location:
			headers.append(('Location', location))
		if extra_headers:
			headers.extend(extra_headers)
		self.headers = headers

	def set_cookie(self, key: str, value: typing.Any, domain: str | None=None, path: str='/',
			expires: datetime.datetime | None=None, max_age: datetime.timedelta | None=None, secure: bool=False,
			http_only: bool=False) -> None:
		"""
		adds a Set-Cookie header

		:type expires: datetime.datetime
		:param expires: if set to a value in the past, the cookie is deleted. if this and ``max_age`` are
		  not set, the cookie becomes a session cookie.
		:type max_age: datetime.timedelta
		:param max_age: according to the spec, has precedence over expires. if you specify both, both are sent.
		:param secure: controls when the browser sends the cookie back - unrelated to :func:`set_secure_cookie`

		see `the docs <https://tools.ietf.org/html/rfc6265#section-4.1>`_ for an explanation of the other params
		"""
		cookie = '%s=%s' % (key, self.simple_cookie.value_encode(value)[1])
		if domain:
			cookie += '; Domain=%s' % domain
		if path:
			cookie += '; Path=%s' % path
		if expires:
			cookie += '; Expires=%s' % expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
		if max_age is not None:
			cookie += '; Max-Age=%d' % max_age.total_seconds()
		if secure:
			cookie += '; Secure'
		if http_only:
			cookie += '; HttpOnly'
		self.headers.append(('Set-Cookie', cookie))

	def set_secure_cookie(self, request: Request, key: str, value: typing.Any, **kwargs: typing.Any) -> None:
		"""
		this function accepts the same keyword arguments as :func:`.set_cookie` but stores a
		timestamp and a signature based on ``request.app.cookie_secret``. decode with
		:func:`Request.get_secure_cookie`.

		the signature is a SHA-256 `hmac <https://docs.python.org/3/library/hmac.html>`_ of the
		key, value, and timestamp. the value is *not* encrypted and is readable by the user, but is
		signed and tamper-proof (assuming the ``cookie_secret`` is secure). because we store the
		signing time, expiry is checked with ``get_secure_cookie``. you generally will want to pass
		this function a ``max_age`` equal to ``max_time`` used when reading the cookie.
		"""
		assert request.app.cookie_secret is not None
		ts = int(time.time())
		value_ts = '%s|%s' % (value, ts)
		signature = _hash(key + '|' + value_ts, request.app.cookie_secret)
		value_signed = '%s|%s' % (value_ts, signature)
		self.set_cookie(key, value_signed, **kwargs)

	@classmethod
	def json(cls, obj: typing.Any) -> Response:
		"""
		generate a streaming :class:`.Response` object from an object with an ``application/json``
		content type. the default :attr:`.json_encoder` indents with tabs - override if you want
		different indentation or need special encoding.
		"""
		body = cls._gen_json(obj)
		return Response(body, content_type='application/json; charset=utf-8')

	@classmethod
	def _gen_json(cls, obj: typing.Any) -> typing.Iterator[bytes]:
		"""
		internal use generator for converting
		`json.JSONEncoder.iterencode <https://docs.python.org/3/library/json.html#json.JSONEncoder.iterencode>`_
		output to bytes
		"""
		for chunk in cls.json_encoder.iterencode(obj):
			yield chunk.encode('utf-8')

	@classmethod
	def render(cls, request: Request, template: str, context: dict[str, typing.Any]) -> 'Response':
		"""
		generate a streaming :class:`.Response` object from a template and a context with a
		``text/html`` content type.

		:type request: :class:`.Request`
		:param request: the request to generate the response for
		:type template: str
		:param template: the template name to render, relative to ``request.app.template_dir``
		:param context: if you used the default jinja2 template engine, this is a dict

		"""
		body = request.app.template_engine.render(template, context)
		response = cls(body, content_type='text/html; charset=utf-8')
		return response

def _hash(value_ts: str, cookie_secret: bytes) -> str:
	h = hmac.new(cookie_secret, value_ts.encode(), hashlib.sha256)
	signature = h.hexdigest()
	return signature

class HTTPHeaders(UserDict): # inherit so that __init__ and fromkeys work (even though we never use them)
	"""
	behaves like a regular :class:`dict` but
	`casefolds <https://docs.python.org/3/library/stdtypes.html#str.casefold>`_ the keys
	"""

	def __setitem__(self, key: str, value: str) -> None:
		self.data[key.casefold()] = value

	def __getitem__(self, key: str) -> str:
		return self.data[key.casefold()]
