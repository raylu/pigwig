import unittest

from pigwig import exceptions
from pigwig.routes import build_route_tree

class RouteTests(unittest.TestCase):
	def test_simple(self):
		t = build_route_tree([
			('GET', '/', 0),
			('GET', '/one', 1),
			('POST', '/two/three', 2),
		])
		self.assertEqual(t.route('GET', '/'), (0, {}))
		self.assertEqual(t.route('GET', '/one'), (1, {}))
		self.assertEqual(t.route('POST', '/two/three'), (2, {}))
		with self.assertRaises(exceptions.HTTPException):
			t.route('POST', '/two')
		with self.assertRaises(exceptions.HTTPException):
			t.route('GET', '/two/three')

	def test_params(self):
		t = build_route_tree([
			('GET', '/one', 1),
			('GET', '/<p1>', 2),
			('GET', '/<p1>/three', 3),
			('GET', '/<p1>/<p2>', 2),
		])
		self.assertEqual(t.route('GET', '/one'), (1, {}))
		self.assertEqual(t.route('GET', '/two'), (2, {'p1': 'two'}))
		self.assertEqual(t.route('GET', '/two/three'), (3, {'p1': 'two'}))
		self.assertEqual(t.route('GET', '/two/foo'), (2, {'p1': 'two', 'p2': 'foo'}))

	def test_conflict(self):
		with self.assertRaises(exceptions.RouteConflict):
			build_route_tree([
				('GET', '/<p1>', 1),
				('GET', '/<p2>', 2),
			])
		with self.assertRaises(exceptions.RouteConflict):
			build_route_tree([
				('GET', '/one/', 1),
				('GET', '/one/', 2),
			])
		with self.assertRaises(Exception):
			build_route_tree([
				('GET', '/<p1>//', 1),
			])
