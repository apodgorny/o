import os
import shutil
import struct

import o


class Field(o.Module):

	SOURCE_MARKER   = '__is_source__'
	TAG_STR        = 1
	TAG_INT        = 2
	TAG_BOOL       = 3
	TAG_FLOAT      = 4
	TAG_NULL       = 5

	_TAG_TO_ANNOTATION = {
		TAG_STR   : str,
		TAG_INT   : int,
		TAG_BOOL  : bool,
		TAG_FLOAT : float,
		TAG_NULL  : type(None),
	}

	_ANNOTATION_TO_TAG = {
		str        : TAG_STR,
		int        : TAG_INT,
		bool       : TAG_BOOL,
		float      : TAG_FLOAT,
		type(None) : TAG_NULL,
	}

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, fields_path, name):
		self.fields_path = fields_path
		self.name        = name
		self.path        = os.path.join(fields_path, name)

		os.makedirs(self.path, exist_ok=True)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Get property path
	# ----------------------------------------------------------------------
	def _get_prop_file_path(self, prop_name):
		return os.path.join(self.path, prop_name)

	# Encode atomic field prop into bytes with a stable type prefix
	# ----------------------------------------------------------------------
	def _encode_prop_value(self, value):
		annotation = str
		tag        = self.TAG_STR
		data       = b''

		if value is o.Undefined:
			data = b''
		else:
			annotation = o.Annotation.annotate(value).annotation

			if annotation is None:
				annotation = type(None)

			tag = self._ANNOTATION_TO_TAG.get(annotation)

			if tag is None:
				raise TypeError(f'Unsupported field prop value annotation `{annotation}`')

			if annotation is str:
				data = value.encode('utf-8')
			elif annotation is type(None):
				data = b''
			else:
				data = str(value).encode('utf-8')

		return struct.pack('<Q', tag) + data

	# Decode atomic field prop from bytes with a stable type prefix
	# ----------------------------------------------------------------------
	def _decode_prop_value(self, data):
		tag        = struct.unpack('<Q', data[:8])[0]
		value_data = data[8:]
		annotation = self._TAG_TO_ANNOTATION.get(tag)
		value      = None

		if annotation is None:
			raise ValueError(f'Unknown field prop type tag `{tag}`')
		elif annotation is str:
			value = value_data.decode('utf-8')
		elif annotation is type(None):
			value = None
		else:
			value = o.Annotation(annotation).cast(value_data.decode('utf-8'))

		return value

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Write field properties
	# ----------------------------------------------------------------------
	def write(self, props):
		for prop_name, prop_value in props.items():
			if prop_name == 'default':
				if prop_value is not o.Undefined:
					self.set(prop_name, prop_value)
			else:
				self.set(prop_name, prop_value)

		if (
			'default' not in props
			or props.get('default', o.Undefined) is o.Undefined
		) and self.has('default'):
			self.remove('default')

	# Remove field properties and room
	# ----------------------------------------------------------------------
	def clear(self):
		if os.path.exists(self.path):
			shutil.rmtree(self.path)

	# Mark field as source-backed
	# ----------------------------------------------------------------------
	def mark_source(self):
		open(os.path.join(self.path, self.SOURCE_MARKER), 'wb').close()

	# Check whether field is source-backed
	# ----------------------------------------------------------------------
	def is_source(self):
		return self.has(self.SOURCE_MARKER)

	# Set field property
	# ----------------------------------------------------------------------
	def set(self, prop_name, value=o.Undefined):
		path = self._get_prop_file_path(prop_name)
		data = self._encode_prop_value(value)

		with open(path, 'wb') as file:
			file.write(data)

	# Get field property
	# ----------------------------------------------------------------------
	def get(self, prop_name):
		path  = self._get_prop_file_path(prop_name)
		data  = None
		value = None

		if os.path.exists(path):
			with open(path, 'rb') as file:
				data = file.read()

			value = self._decode_prop_value(data)

		return value

	# Remove field property
	# ----------------------------------------------------------------------
	def remove(self, prop_name):
		path = self._get_prop_file_path(prop_name)

		if os.path.exists(path):
			os.remove(path)

	# Check field property
	# ----------------------------------------------------------------------
	def has(self, prop_name):
		return os.path.exists(self._get_prop_file_path(prop_name))

	# Read directory of properties and each file
	# ----------------------------------------------------------------------
	@property
	def properties(self):
		for prop_name in os.listdir(self.path):
			if prop_name != self.SOURCE_MARKER:
				yield prop_name, self.get(prop_name)
