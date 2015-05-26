try:
	import jinja2
except ImportError:
	jinja2 = None

class JinjaTemplateEngine:
	def __init__(self, template_dir):
		if not jinja2:
			raise Exception('Cannot use %s without jinja2 installed' % self.__class__)
		loader = jinja2.FileSystemLoader(template_dir)
		self.jinja_env = jinja2.Environment(loader=loader)

	def render(self, template_name, context):
		template = self.jinja_env.get_template(template_name)
		stream = template.stream(context)
		stream.enable_buffering()
		for chunk in stream:
			yield chunk.encode('utf-8')
