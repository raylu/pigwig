class HTTPException(Exception):
	def __init__(self, code, body):
		super().__init__(code, body)
		self.code = code
		self.body = body

class RouteConflict(Exception):
	pass
