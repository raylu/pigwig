import os
import sys
import _thread # pylint: disable=unused-import

from . import inotify

def init():
	fd = inotify.init()
	wds = {}
	for module in sys.modules.values():
		try:
			pathname = module.__file__
		except AttributeError:
			continue
		if pathname is None:
			continue
		wd = inotify.add_watch(fd, pathname, inotify.IN.CLOSE_WRITE)
		wds[wd] = pathname

	# pylint: disable=redefined-outer-name,import-outside-toplevel
	try:
		import eventlet
	except ImportError:
		pass
	else:
		_thread = eventlet.patcher.original('_thread')
	_thread.start_new_thread(_reloader, (fd, wds))

def _reloader(fd, wds):
	events = inotify.get_events(fd)
	for event in events:
		print(wds[event.wd], 'changed, reloading...')
	do_reload(fd)

def do_reload(fd):
	os.close(fd)
	os.closerange(sys.stderr.fileno()+1, os.sysconf('SC_OPEN_MAX')) # close keep-alive client sockets
	os.execv(sys.argv[0], sys.argv)
