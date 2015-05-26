#!/usr/bin/env python3

from pigwig import PigWig

def routes():
	return [
		('/', root),
	]

def root(request):
	return request.render('root.jinja2', {})

app = PigWig(routes, template_dir='templates')

if __name__ == '__main__':
	app.main()
