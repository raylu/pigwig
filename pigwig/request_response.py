class Request:
	def __init__(self, app, query):
		self.app = app
		self.query = query

	def render(self, template, context):
		body = self.app.template_engine.render(template, context)
		return Response(body, content_type='text/html')

class Response:
	def __init__(self, body, content_type='text/plain'):
		self.body = body
		self.content_type = content_type
