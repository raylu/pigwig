import os
import sys
import typing

from fsevents import Observer, Stream  # type: ignore[import-not-found]

if typing.TYPE_CHECKING:
	from fsevents import FileEvent

observer = Observer()
observer.daemon = True

def callback(event: FileEvent) -> typing.NoReturn:
	observer.stop()
	print(event.name, 'changed, reloading...')
	os.execv(sys.argv[0], sys.argv)

def init() -> None:
	paths = []
	for module in sys.modules.values():
		try:
			pathname = os.path.dirname(module.__file__) # type: ignore[type-var]
		except (AttributeError, TypeError):
			continue
		paths.append(pathname)

	observer.start()
	stream = Stream(callback, *paths, file_events=True)
	observer.schedule(stream)
