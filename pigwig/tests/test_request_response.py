import json
import unittest

from pigwig import Response

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
