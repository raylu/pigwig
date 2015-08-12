class HTTPException(Exception):
	'''
	raise in a route handler to generate a non-200 response

	:param code: interpreted the same way as :attr:`.Response.code`
	:param body: unlike in :class:`.Response`, must be a ``str``
	'''

	def __init__(self, code, body):
		super().__init__(code, body)
		self.code = code
		self.body = body

class RouteConflict(Exception):
	'''
	raised when creating a :class:`.PigWig` app if two routes conflict
	'''
