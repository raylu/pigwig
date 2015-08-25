import http.cookies
import json
import unittest

from pigwig import PigWig, Request, Response
from pigwig.request_response import HTTPHeaders

class ResponseTests(unittest.TestCase):
	def test_json(self):
		r = Response.json(None)
		self.assertEqual(next(r.body), b'null')

		big_obj = ['a' * 256] * 256
		r = Response.json(big_obj)
		chunks = list(r.body)
		self.assertGreater(len(chunks), 1)

		Response.json_encoder = json.JSONEncoder()
		r = Response.json(big_obj)
		chunks = list(r.body)
		self.assertGreater(len(chunks), 1)
		self.assertEqual(b''.join(chunks), json.dumps(big_obj).encode())

	def test_secure_cookie(self):
		app = PigWig([], cookie_secret=b'a|b')
		req = Request(app, None, None, None, None, None, None, None)
		r = Response()
		r.set_secure_cookie(req, 'c|d', 'e|f')
		set_cookie = r.headers[-1]
		self.assertEqual(set_cookie[0], 'Set-Cookie')

		cookies = http.cookies.SimpleCookie(set_cookie[1])
		req.cookies = cookies
		self.assertEqual(req.get_secure_cookie('c|d', None), 'e|f')

class HTTPHeadersTests(unittest.TestCase):
	def test(self):
		h = HTTPHeaders()
		h['COOKIE'] = 'abc'
		self.assertEqual(h['cookie'], 'abc')
