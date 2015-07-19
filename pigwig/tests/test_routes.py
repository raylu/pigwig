import unittest

from pigwig import exceptions
from pigwig.routes import RouteTree

class RouteTests(unittest.TestCase):
	def test_simple(self):
		t = RouteTree([
			('GET', '/', 0),
			('GET', '/one', 1),
			('POST', '/two/three', 2),
		])
		self.assertEqual(t.get_route('GET', '/'), (0, {}))
		self.assertEqual(t.get_route('GET', '/one'), (1, {}))
		self.assertEqual(t.get_route('POST', '/two/three'), (2, {}))
		with self.assertRaises(exceptions.HTTPException):
			t.get_route('POST', '/two')
		with self.assertRaises(exceptions.HTTPException):
			t.get_route('GET', '/two/three')

	def test_params(self):
		t = RouteTree([
			('GET', '/one', 1),
			('GET', '/<p1>', 2),
			('GET', '/<p1>/three', 3),
			('GET', '/<p1>/<p2>', 2),
		])
		self.assertEqual(t.get_route('GET', '/one'), (1, {}))
		self.assertEqual(t.get_route('GET', '/two'), (2, {'p1': 'two'}))
		self.assertEqual(t.get_route('GET', '/two/three'), (3, {'p1': 'two'}))
		self.assertEqual(t.get_route('GET', '/two/foo'), (2, {'p1': 'two', 'p2': 'foo'}))

	def test_conflict(self):
		with self.assertRaises(exceptions.RouteConflict):
			RouteTree([
				('GET', '/<p1>', 1),
				('GET', '/<p2>', 2),
			])
		with self.assertRaises(exceptions.RouteConflict):
			RouteTree([
				('GET', '/one/', 1),
				('GET', '/one/', 2),
			])
		with self.assertRaises(Exception):
			RouteTree([
				('GET', '/<p1>//', 1),
			])
