PigWig
======

.. py:module:: pigwig

pigwig is a WSGI framework for python 3.6+::

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

pigwig has no hard dependencies, but

1. if you want to use templating, you must either install `jinja2 <http://jinja.pocoo.org/docs>`_
   or provide your own template engine
2. if you want to use :func:`PigWig.main` for development, the reloader requires a libc that
   supports inotify (linux 2.6.13 and glibc 2.4 or later) or the
   `macfsevents <https://github.com/malthe/macfsevents>`_ package on OS X
3. you will want a "real" WSGI server to deploy on such as
   `eventlet <http://eventlet.net/doc/modules/wsgi.html>`_ or `gunicorn <http://gunicorn.org/#quickstart>`_

see `blogwig <https://github.com/raylu/pigwig/tree/master/blogwig>`_ for a more in-depth example
and the `readme <https://github.com/raylu/pigwig#facs-frequent-annoying-comments>`_ for FACs

.. toctree::
   :maxdepth: 2

   pigwig
   request_response
   multipart
   exceptions

indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

