try:
	import jinja2
except ImportError:
	jinja2 = None

class JinjaTemplateEngine:
	def __init__(self, template_dir):
		if not jinja2:
			raise Exception('Cannot use %s without jinja2 installed' % self.__class__)
		loader = jinja2.FileSystemLoader(template_dir)
		self.jinja_env = jinja2.Environment(loader=loader, auto_reload=False)

	def render(self, template_name, context):
		template = self.jinja_env.get_template(template_name)
		return template.render(context)
