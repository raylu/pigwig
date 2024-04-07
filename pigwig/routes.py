import re
import textwrap
from typing import Callable

from . import exceptions

class RouteNode:
	def __init__(self) -> None:
		self.method_handlers: dict[str, Callable] = {}
		self.static_children: dict[str, RouteNode] = {}
		self.param_name: str | None = None
		self.param_children: RouteNode | None = None
		self.param_is_path: bool | None = None

	param_re = re.compile(r'<([\w:]+)>')
	def assign_route(self, path_elements: list[str], method: str, handler: Callable) -> None:
		if not path_elements or path_elements[0] == '':
			if len(path_elements) > 1:
				raise Exception('cannot have consecutive / in routes')
			if method in self.method_handlers:
				raise exceptions.RouteConflict(method, handler)
			self.method_handlers[method] = handler
			return

		element = path_elements[0]
		remaining = path_elements[1:]
		param = self.param_re.match(element)
		if param:
			if self.param_name is None:
				self.param_name = param.group(1)
				self.param_children = RouteNode()
				if self.param_name.startswith('path:'):
					self.param_is_path = True
					self.param_name = self.param_name[5:]
					remaining = []
				else:
					self.param_is_path = False
			elif self.param_name != param.group(1):
				raise exceptions.RouteConflict(method, handler)
			else:
				assert self.param_children is not None
			child = self.param_children
		else:
			if element not in self.static_children:
				self.static_children[element] = RouteNode()
			child = self.static_children[element]

		child.assign_route(remaining, method, handler)

	def get_route(self, method: str, path_elements: list[str], params: dict[str, str]) -> tuple[Callable, dict]:
		if not path_elements or path_elements[0] == '':
			handler = self.method_handlers.get(method)
			if handler is not None:
				return handler, params
			elif self.method_handlers:
				raise exceptions.HTTPException(405, 'method %s not allowed' % method)
			else:
				raise exceptions.HTTPException(404, 'route not found')

		element = path_elements[0]
		remaining = path_elements[1:]
		child = self.static_children.get(element)
		if child is None:
			if self.param_name is None:
				raise exceptions.HTTPException(404, 'route not found')
			if self.param_is_path:
				params[self.param_name] = '/'.join(path_elements)
				remaining = []
			else:
				params[self.param_name] = element
			child = self.param_children
			assert child is not None
		return child.get_route(method, remaining, params)

	def route(self, method: str, path: str) -> tuple[Callable, dict]:
		path_elements = path[1:].split('/')
		return self.get_route(method, path_elements, {})

	def __str__(self) -> str:
		rval = []
		for method, handler in self.method_handlers.items():
			rval.append('%s: %s,' % (method, handler))
		for element, node in self.static_children.items():
			rval.append('%r: %s' % (element, node))
		if self.param_name:
			name = self.param_name
			if self.param_is_path:
				name += ' (path)'
			rval.append('%s: %s' % (name, self.param_children))
		return '{\n%s\n}' % textwrap.indent('\n'.join(rval), '\t')

RouteDefinition = list[tuple[str, str, Callable]]

def build_route_tree(routes: RouteDefinition) -> RouteNode:
	root_node = RouteNode()
	for method, path, handler in routes:
		path_elements = path[1:].split('/')
		root_node.assign_route(path_elements, method, handler)
	return root_node
