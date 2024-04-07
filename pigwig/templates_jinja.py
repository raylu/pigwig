from __future__ import annotations

import types
import typing

try:
	import jinja2
except ImportError:
	jinja2: types.ModuleType = None # type: ignore[no-redef]

class JinjaTemplateEngine:
	def __init__(self, template_dir: str) -> None:
		if not jinja2:
			raise Exception('Cannot use %s without jinja2 installed' % self.__class__)
		loader = jinja2.FileSystemLoader(template_dir)
		self.jinja_env = jinja2.Environment(loader=loader, auto_reload=False)

	def render(self, template_name: str, context: dict[str, typing.Any]) -> str:
		template = self.jinja_env.get_template(template_name)
		return template.render(context)
