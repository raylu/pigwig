import textwrap
import re

from . import exceptions

class RouteNode(dict):
	def __init__(self):
		super().__init__()
		self.method_handlers = {}
		self.param_name = self.param_children = None

	param_re = re.compile(r'<(\w+)>')
	def assign_route(self, path_elements, method, handler):
		if not path_elements or path_elements[0] == '':
			if len(path_elements) > 1:
				raise Exception('cannot have consecutive / in routes')
			if method in self.method_handlers:
				raise exceptions.RouteConflict(method, handler)
			self.method_handlers[method] = handler
			return

		element = path_elements[0]
		param = self.param_re.match(element)
		if param:
			if self.param_name is None:
				self.param_name = param.group(1)
				self.param_children = RouteNode()
			elif self.param_name != param.group(1):
				raise exceptions.RouteConflict(method, handler)
			child = self.param_children
		else:
			if element not in self:
				self[element] = RouteNode()
			child = self[element]

		child.assign_route(path_elements[1:], method, handler)

	def get_route(self, method, path_elements, params):
		if not path_elements or path_elements[0] == '':
			handler = self.method_handlers.get(method)
			if handler is not None:
				return handler, params
			elif self.method_handlers:
				raise exceptions.HTTPException(405, 'method %s not allowed' % method)
			else:
				raise exceptions.HTTPException(404, 'route not found')

		element = path_elements[0]
		child = self.get(element)
		if child is None:
			if self.param_name is None:
				raise exceptions.HTTPException(404, 'route not found')
			params[self.param_name] = element
			child = self.param_children
		return child.get_route(method, path_elements[1:], params)

	def __str__(self):
		rval = []
		for method, handler in self.method_handlers.items():
			rval.append('%s: %s,' % (method, handler))
		for element, node in self.items():
			rval.append('%r: %s' % (element, node))
		if self.param_name:
			rval.append('%s: %s' % (self.param_name, self.param_children))
		return '{\n%s\n}' % textwrap.indent('\n'.join(rval), '\t')

class RouteTree(RouteNode):
	def __init__(self, routes):
		super().__init__()

		for method, path, handler in routes:
			path_elements = path[1:].split('/')
			self.assign_route(path_elements, method, handler)

	def get_route(self, method, path):
		path_elements = path[1:].split('/')
		return super().get_route(method, path_elements, {})
