from __future__ import annotations

import http.client
import io
import re
import typing

maxlen = 1024 * 1024 * 1024 # 1 GB

def parse_multipart(fp: io.BufferedIOBase, pdict: dict) -> dict[str, list[bytes | MultipartFile]]:
	"""
		most of this code is copied straight from
		`cgi.parse_multipart <https://github.com/python/cpython/blob/ad76602f69d884e491b0913c641dd8e42902c36c/Lib/cgi.py#L201>`_.
		the only difference is that it returns a :class:`.MultipartFile` for any part with a ``filename``
		param in its content-disposition (instead of just the bytes).
	"""
	boundary = pdict.get('boundary', b'')
	if re.match(b'^[ -~]{0,200}[!-~]$', boundary) is None:
		raise ValueError('Invalid boundary in multipart form: %r' % boundary)

	nextpart = b'--' + boundary
	lastpart = b'--' + boundary + b'--'
	partdict: dict[str, list[bytes | MultipartFile]] = {}
	terminator = b''
	while terminator != lastpart:
		read = -1
		data: bytes | MultipartFile | None = None
		if terminator:
			# At start of next part.  Read headers first.
			headers = http.client.parse_headers(fp)
			clength = headers.get('content-length')
			if clength:
				try:
					read = int(clength)
				except ValueError:
					pass
			if read > 0:
				if maxlen and read > maxlen:
					raise ValueError('Maximum content length exceeded')
				data = fp.read(read)
			else:
				data = b''
		# read lines until end of part
		lines = []
		while True:
			line = fp.readline()
			if not line:
				terminator = lastpart
				break
			if line.startswith(b'--'):
				terminator = line.rstrip()
				if terminator in (nextpart, lastpart):
					break
			lines.append(line)
		# done with part
		if data is None:
			continue
		if read < 0:
			if lines:
				# strip final line terminator
				line = lines[-1]
				if line[-2:] == b'\r\n':
					line = line[:-2]
				elif line[-1:] == b'\n':
					line = line[:-1]
				lines[-1] = line
				data = b''.join(lines)
		content_disposition = headers['content-disposition']
		if not content_disposition:
			continue
		key, params = parse_header(content_disposition)
		if key != 'form-data':
			continue
		if 'name' in params:
			name = params['name']
		else:
			continue

		if 'filename' in params:
			assert isinstance(data, bytes)
			data = MultipartFile(data, params['filename'])
		if name in partdict:
			partdict[name].append(data)
		else:
			partdict[name] = [data]

	return partdict

def parse_header(line: str) -> tuple[str, dict[str, str]]:
	"""Parse a Content-type like header.

	Return the main content-type and a dictionary of options.
	"""
	parts = _parseparam(';' + line)
	key = parts.__next__()
	pdict = {}
	for p in parts:
		i = p.find('=')
		if i >= 0:
			name = p[:i].strip().lower()
			value = p[i+1:].strip()
			if len(value) >= 2 and value[0] == value[-1] == '"':
				value = value[1:-1]
				value = value.replace('\\\\', '\\').replace('\\"', '"')
			pdict[name] = value
	return key, pdict

def _parseparam(s: str) -> typing.Iterator[str]:
	while s[:1] == ';':
		s = s[1:]
		end = s.find(';')
		while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
			end = s.find(';', end + 1)
		if end < 0:
			end = len(s)
		f = s[:end]
		yield f.strip()
		s = s[end:]

class MultipartFile:
	"""
		instance attrs:

		* ``data`` - a bytes
		* ``filename`` - a str
	"""
	def __init__(self, data: bytes, filename: str) -> None:
		self.data = data
		self.filename = filename

	def __repr__(self) -> str:
		return '%s(%r, %r)' % (self.__class__.__name__, self.data, self.filename)
