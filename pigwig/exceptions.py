class HTTPException(Exception):
	"""
	raise in a route handler to generate a non-200 response

	:param code: interpreted the same way as [Response.code][]
	:param body: unlike in [Response][], must be a ``str``
	"""

	def __init__(self, code: int, body: str) -> None:
		super().__init__(code, body)
		self.code = code
		self.body = body

class RouteConflict(Exception):
	"""
	raised when creating a [PigWig][] app if two routes conflict
	"""
