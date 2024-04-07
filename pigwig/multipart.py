import cgi
import http.client

maxlen = 1024 * 1024 * 1024 # 1 GB

def parse_multipart(fp, pdict):
	"""
		most of this code is copied straight from
		`cgi.parse_multipart <https://github.com/python/cpython/blob/ad76602f69d884e491b0913c641dd8e42902c36c/Lib/cgi.py#L201>`_.
		the only difference is that it returns a :class:`.MultipartFile` for any part with a ``filename``
		param in its content-disposition (instead of just the bytes).
	"""
	boundary = pdict.get('boundary', b'')
	if not cgi.valid_boundary(boundary):
		raise ValueError('Invalid boundary in multipart form: %r' % boundary)

	nextpart = b'--' + boundary
	lastpart = b'--' + boundary + b'--'
	partdict = {}
	terminator = b''
	while terminator != lastpart:
		read = -1
		data = None
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
		line = headers['content-disposition']
		if not line:
			continue
		key, params = cgi.parse_header(line)
		if key != 'form-data':
			continue
		if 'name' in params:
			name = params['name']
		else:
			continue

		if 'filename' in params:
			data = MultipartFile(data, params['filename'])
		if name in partdict:
			partdict[name].append(data)
		else:
			partdict[name] = [data]

	return partdict

class MultipartFile:
	"""
		instance attrs:

		* ``data`` - a bytes
		* ``filename`` - a str
	"""
	def __init__(self, data, filename):
		self.data = data
		self.filename = filename

	def __repr__(self):
		return '%s(%r, %r)' % (self.__class__.__name__, self.data, self.filename)
