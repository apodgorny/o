import base64

import o


class Base64(o.Service):
	def initialize(self): pass

	def encode(self, n, digits=2):
		# 1. Determine how many bytes are needed to represent the number
		# (n.bit_length() + 7) // 8 calculates minimum bytes required
		byte_length = (n.bit_length() + 7) // 8 or 1
		
		# 2. Convert integer to bytes (Big Endian)
		b_data = n.to_bytes(byte_length, 'big')
		
		# 3. Encode to base64 and decode to string
		# .strip('=') removes standard B64 padding if you want raw digits
		encoded = base64.b64encode(b_data).decode('utf-8').strip('=')
		
		# 4. Zero-pad the resulting B64 string to the desired length
		# Note: 'A' is the Base64 equivalent of zero
		return encoded.rjust(digits, 'A')


	def decode(self, s):
		# 1. Restore '=' padding if necessary to make length a multiple of 4
		missing_padding = len(s) % 4
		if missing_padding:
			s += '=' * (4 - missing_padding)
		
		# 2. Decode the Base64 string into bytes
		b_data = base64.b64decode(s)
		
		# 3. Convert bytes back into an integer (Big Endian)
		return int.from_bytes(b_data, 'big')