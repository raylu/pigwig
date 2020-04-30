import io
import math
import textwrap
import unittest
from unittest import mock

from pigwig import PigWig
from pigwig.exceptions import HTTPException
from pigwig.pigwig import parse_qs

class PigWigTests(unittest.TestCase):
	def test_build_request(self):
		app = PigWig([])
		environ = {
			'REQUEST_METHOD': 'test method',
			'PATH_INFO': 'test path?a=1&b=2&b=3',
			'HTTP_COOKIE': 'a=1; a="2"',
			'wsgi.input': None,
		}
		req, err = app.build_request(environ)
		self.assertIsNone(err)
		self.assertEqual(req.method, 'test method')
		self.assertEqual(req.path, 'test path?a=1&b=2&b=3')
		self.assertEqual(req.query, {})
		self.assertEqual(req.cookies['a'].value, '2')

		environ['QUERY_STRING'] = 'a=1&b=2&b=3'
		req, err = app.build_request(environ)
		self.assertIsNone(err)
		self.assertEqual(req.query, {'a': '1', 'b': ['2', '3']})

		environ['CONTENT_TYPE'] = 'application/json; charset=utf8'
		environ['wsgi.input'] = io.BytesIO(b'{"a": 1, "a": NaN}')
		req, err = app.build_request(environ)
		self.assertIsNone(err)
		self.assertTrue(math.isnan(req.body['a']))

		environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
		environ['wsgi.input'] = io.BytesIO(b'a=1&b=2&b=3')
		req, err = app.build_request(environ)
		self.assertIsNone(err)
		self.assertEqual(req.body, {'a': '1', 'b': ['2', '3']})

		environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded; charset=latin1'
		environ['wsgi.input'] = io.BytesIO('a=Ï'.encode('latin-1')) # capital I with diaresis, 0xCF in latin-1
		req, err = app.build_request(environ)
		self.assertIsNone(err)
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
		req, err = app.build_request(environ)
		self.assertIsNone(err)
		self.assertEqual(req.body['a'], [b'1', b'2'])
		self.assertEqual(req.body['file1'].data, b'blah blah blah')
		self.assertEqual(req.body['file1'].filename, 'the_file')

	def test_parse_qs(self):
		r = parse_qs('a=1&b=2')
		self.assertEqual(r, {'a': '1', 'b': '2'})

		self.assertRaises(HTTPException, parse_qs, 'a=1&b')

		self.assertRaises(HTTPException, parse_qs, 'a=%80')

	def test_exception_handling(self):
		start_response = mock.MagicMock()
		environ = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/', 'wsgi.input': None, 'wsgi.errors': io.StringIO()}

		app = PigWig([])
		app(environ, start_response)
		start_response.assert_called_with('404 Not Found', mock.ANY)

		heh = mock.MagicMock()
		app = PigWig([], http_exception_handler=heh)
		app(environ, start_response)
		# pylint: disable=unsubscriptable-object
		http_exception = heh.call_args[0][0]
		self.assertEqual(http_exception.code, 404)

		eh = mock.MagicMock()
		app = PigWig([('GET', '/', lambda req: 0/0)], exception_handler=eh)
		app(environ, start_response)
		exception = eh.call_args[0][0]
		self.assertIsInstance(exception, ZeroDivisionError)

		heh.reset()
		eh.reset()
		heh.side_effect = NotADirectoryError()
		app = PigWig([], http_exception_handler=heh, exception_handler=eh)
		app(environ, start_response)
		self.assertTrue(heh.called)
		exception = eh.call_args[0][0]
		self.assertIsInstance(exception, NotADirectoryError)
