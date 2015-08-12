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

	def stream(self, template_name, context):
		# generate jinja2.Template object first, potentially throwing TemplateNotFound
		template = self.jinja_env.get_template(template_name)
		stream = template.stream(context)
		stream.enable_buffering()
		# return byte generator (which isn't executed until headers have been sent)
		return self.stream_gen(stream)

	def stream_gen(self, stream):
		for chunk in stream:
			yield chunk.encode('utf-8')
