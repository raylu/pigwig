from collections import namedtuple
import ctypes
import ctypes.util
from enum import IntEnum
import errno
import os
import struct

libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('c'))
libc.__errno_location.restype = ctypes.POINTER(ctypes.c_int)

Event = namedtuple('Event', ['wd', 'mask', 'cookie', 'name'])

def geterr():
	return errno.errorcode[libc.__errno_location().contents.value]

def init():
	fd = libc.inotify_init()
	if fd == -1:
		raise OSError('inotify_init error', geterr())
	return fd

def add_watch(fd, path, mask):
	wd = libc.inotify_add_watch(fd, path.encode(), mask)
	if wd == -1:
		raise OSError('inotify_add_watch error', geterr())
	return wd

def rm_watch(fd, wd):
	result = libc.inotify_rm_watch(fd, wd)
	if result == -1:
		raise OSError('inotify_rm_watch', geterr())

def get_events(fd):
	buf = b''
	while True:
		data = os.read(fd, 4096)
		buf += data
		if len(data) < 4096:
			break
	pos = end = 0
	while pos < len(buf):
		end += 16
		wd, mask, cookie, name_len = struct.unpack('iIII', buf[pos:end])
		pos = end
		end = end + name_len
		name = struct.unpack('%ds' % name_len, buf[pos:end])
		name = name[0].rstrip(b'\0')
		yield Event(wd, mask, cookie, name.decode())
		pos = end

class IN(IntEnum):
	ACCESS = 0x00000001
	MODIFY = 0x00000002
	ATTRIB = 0x00000004
	CLOSE_WRITE = 0x00000008
	CLOSE_NOWRITE = 0x00000010
	OPEN = 0x00000020
	MOVED_FROM = 0x00000040
	MOVED_TO = 0x00000080
	CREATE = 0x00000100
	DELETE = 0x00000200
	DELETE_SELF = 0x00000400
	MOVE_SELF = 0x00000800
	UNMOUNT	= 0x00002000
	Q_OVERFLOW = 0x00004000
	IGNORED = 0x00008000
	ONLYDIR = 0x01000000
	DONT_FOLLOW = 0x02000000
	MASK_ADD = 0x20000000
	ISDIR = 0x40000000
	ONESHOT = 0x80000000
