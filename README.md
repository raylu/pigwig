# pigwig

a pig wearing a wig is humor  
a wig wearing a pig is heresy  
pigwig is a python 3 WSGI framework  
(blogwig is a sample app. don't put wigs on blogs)

```python
#!/usr/bin/env python3

from pigwig import PigWig, Response

def root(request):
	return Response('hello, world!')

routes = [
	('GET', '/', root),
]

app = PigWig(routes)

if __name__ == '__main__':
	app.main()
```

### FACs (frequent, annoying comments)

1. **tornado-style class-based views are better**  
we think you're wrong (inheritance is a hammer and this problem is no nail),
but it's easy enough to achieve:
	```python
	def routes():
		views = [
			('/', RootHandler),
		]
		handlers = []
		for route, view in views:
			for verb in ['get', 'post']:
				if hasattr(view, verb):
					handlers.append((verb.upper(), route, cbv_handler(view, verb)))
		return handlers

	def cbv_handler(cbv, verb):
		def handler(request):
			return getattr(cbv(request), verb)()
		return handler

	class RootHandler:
		def __init__(self, request):
			self.request = request

		def get(self):
			return Response('hello')
	```
1. **flask-style decorator-based routing is better**  
we think you're wrong (explicit is better than implicit),
but it's easy enough to achieve:
	```python
	routes = []
	def route(path, method='GET'):
		def wrapper(handler):
			routes.append((method, path, handler))
			return handler
		return wrapper

	@route('/')
	def root(request):
		return Response('hello')
	```
1. **django-style integration with an ORM is better**  
you're wrong
