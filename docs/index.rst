PigWig
======

pigwig is a WSGI framework for python 3.4+::

    #!/usr/bin/env python3

    from pigwig import PigWig, Response

    def root(request):
        return Response('hello, world!')

    def shout(request, word):
        return Response.json({'input': word, 'OUTPUT': word.upper()})

    routes = [
        ('GET', '/', root),
        ('GET', '/shout/<word>', shout),
    ]

    app = PigWig(routes)

    if __name__ == '__main__':
        app.main()

see `blogwig <https://github.com/raylu/pigwig/tree/master/blogwig>`_ for a more in-depth example
and the `readme <https://github.com/raylu/pigwig#facs-frequent-annoying-comments>`_ for FACs

.. toctree::
   :maxdepth: 2

   pigwig
   request_response
   exceptions

indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

