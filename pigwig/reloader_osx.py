import os
import sys

from fsevents import Observer, Stream # type: ignore

observer = Observer()
observer.daemon = True

def callback(event):
	observer.stop()
	print(event.name, 'changed, reloading...')
	os.execv(sys.argv[0], sys.argv)

def init():
	paths = []
	for module in sys.modules.values():
		try:
			pathname = os.path.dirname(module.__file__)
		except (AttributeError, TypeError):
			continue
		paths.append(pathname)

	observer.start()
	stream = Stream(callback, *paths, file_events=True)
	observer.schedule(stream)
