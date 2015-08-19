import io
import math
import textwrap
import unittest

from pigwig import PigWig

class PigWigTests(unittest.TestCase):
	def test_build_request(self):
		app = PigWig([])
		environ = {
			'REQUEST_METHOD': 'test method',
			'PATH_INFO': 'test path?a=1&b=2&b=3',
			'HTTP_COOKIE': 'a=1; a="2"',
			'wsgi.input': None,
		}
		req = app.build_request(environ)
		self.assertEqual(req.method, 'test method')
		self.assertEqual(req.path, 'test path?a=1&b=2&b=3')
		self.assertEqual(req.query, {})
		self.assertEqual(req.cookies['a'].value, '2')

		environ['QUERY_STRING'] = 'a=1&b=2&b=3'
		req = app.build_request(environ)
		self.assertEqual(req.query, {'a': '1', 'b': ['2', '3']})

		environ['CONTENT_TYPE'] = 'application/json; charset=utf8'
		environ['wsgi.input'] = io.BytesIO(b'{"a": 1, "a": NaN}')
		req = app.build_request(environ)
		self.assertTrue(math.isnan(req.body['a']))

		environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
		environ['wsgi.input'] = io.BytesIO(b'a=1&b=2&b=3')
		req = app.build_request(environ)
		self.assertEqual(req.body, {'a': '1', 'b': ['2', '3']})

		environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded; charset=latin1'
		environ['wsgi.input'] = io.BytesIO('a=Ï'.encode('latin-1')) # capital I with diaresis, 0xCF in latin-1
		req = app.build_request(environ)
		self.assertEqual(req.body, {'a': 'Ï'})

		environ['CONTENT_TYPE'] = 'multipart/form-data; boundary=boundary'
		environ['wsgi.input'] = io.BytesIO(textwrap.dedent('''\
		--boundary
		Content-Disposition: form-data; name="a"

		1
		--boundary
		Content-Disposition: form-data; name="a"

		2
		--boundary
		Content-Disposition: form-data; name="file1"; filename="the_file"
		Content-Type: application/octet-stream

		blah blah blah
		--boundary--
		''').encode())
		req = app.build_request(environ)
		self.assertEqual(req.body, {'a': [b'1', b'2'], 'file1': b'blah blah blah'})
