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
