pigwig is a WSGI framework for python 3.6+:

```python
#!/usr/bin/env python3

import typing
from pigwig import PigWig, Response
if typing.TYPE_CHECKING:
    from pigwig import Request
    from pigwig.routes import RouteDefinition

def root(request: Request) -> Response:
    return Response('hello, world!')

def shout(request: Request, word: str) -> Response:
    return Response.json({'input': word, 'OUTPUT': word.upper()})

routes: RouteDefinition = [
    ('GET', '/', root),
    ('GET', '/shout/<word>', shout),
]

app = PigWig(routes)

if __name__ == '__main__':
    app.main()
```

pigwig has no hard dependencies, but

1. if you want to use templating, you must either install [jinja2](http://jinja.pocoo.org/docs)
   or provide your own template engine
2. if you want to use [pigwig.PigWig.main][] for development, the reloader requires a libc that
   supports inotify (linux 2.6.13 and glibc 2.4 or later) or the
   [macfsevents](https://github.com/malthe/macfsevents) package on OS X
3. you will want a "real" WSGI server to deploy on such as
   [waitress](https://docs.pylonsproject.org/projects/waitress),
   [eventlet](https://eventlet.readthedocs.io/en/latest/reference/api/eventlet.html#module-eventlet.wsgi),
   or [gunicorn](https://gunicorn.org/)

see [blogwig](https://github.com/raylu/pigwig/tree/master/blogwig) for a more in-depth example
and the [readme](https://github.com/raylu/pigwig#facs-frequent-annoying-comments) for FACs
