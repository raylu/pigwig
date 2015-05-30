#!/usr/bin/env python3

from pigwig import PigWig, Response

def routes():
	return [
		('/', root),
	]

def root(request):
	return Response.render(request, 'root.jinja2', {})

app = PigWig(routes, template_dir='templates')

if __name__ == '__main__':
	app.main()
