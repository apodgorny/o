import os
import struct

import o


class Store(o.Service):

	def initialize(self):
		self.dir = o.db.store

		self.header_word    = struct.Struct('<QQQQQ128s')
		self.attribute_word = struct.Struct('<32sQ')
		self.ref_word       = struct.Struct('<Q')
		self.dict_item_word = struct.Struct('<QQ')

		self.max_id = self._scan_max_id()

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Scan max object id from store directory
	# ----------------------------------------------------------------------
	def _scan_max_id(self):
		max_id = 0

		for name in os.listdir(self.dir.path):
			if name.isdigit():
				id_ = int(name)

				if id_ > max_id:
					max_id = id_

		return max_id

	# Allocate next object id
	# ----------------------------------------------------------------------
	def _get_new_id(self):
		self.max_id += 1
		return self.max_id

	# Build record file path by id
	# ----------------------------------------------------------------------
	def _get_path(self, id):
		return os.path.join(self.dir.path, str(id))

	# Pack attributes section as `(S32, Q)*`
	# ----------------------------------------------------------------------
	def _pack_attributes(self, attributes):
		parts = []
		items = attributes.items() if isinstance(attributes, dict) else attributes

		for key, ref in items:
			key_bin = key.encode('utf-8')
			key_bin = key_bin[:32]
			key_bin = key_bin.ljust(32, b'\0')
			parts.append(self.attribute_word.pack(key_bin, ref))

		return b''.join(parts)

	# Pack list section as `Q*`
	# ----------------------------------------------------------------------
	def _pack_list(self, items):
		parts = []

		for ref in items:
			parts.append(self.ref_word.pack(ref))

		return b''.join(parts)

	# Pack dict section as `(Q, Q)*`
	# ----------------------------------------------------------------------
	def _pack_dict(self, items):
		parts = []
		pairs = items.items() if isinstance(items, dict) else items

		for key_ref, value_ref in pairs:
			parts.append(self.dict_item_word.pack(key_ref, value_ref))

		return b''.join(parts)

	# Pack proto section as `Q*`
	# ----------------------------------------------------------------------
	def _pack_proto(self, proto_parent, proto_children):
		parent_bin   = b''
		children_bin = self._pack_list(proto_children)

		if proto_parent is not None:
			parent_bin = self.ref_word.pack(proto_parent)

		return parent_bin + children_bin

	# Pack value tail as raw bytes
	# ----------------------------------------------------------------------
	def _pack_value(self, value):
		data = b''

		if value is None:
			data = b''
		elif isinstance(value, bytes):
			data = value
		else:
			raise TypeError(f'Store cannot pack `value` of type `{type(value).__name__}`')

		return data

	# Pack full record from all sections
	# ----------------------------------------------------------------------
	def _pack(
		self,
		o_module,
		attributes,
		list_items,
		dict_items,
		proto_parent,
		proto_children,
		value,
	):
		attributes_bin = self._pack_attributes(attributes)
		list_items_bin = self._pack_list(list_items)
		dict_items_bin = self._pack_dict(dict_items)
		proto_bin      = self._pack_proto(proto_parent, proto_children)
		value_bin      = self._pack_value(value)

		header_size           = self.header_word.size
		list_offset           = header_size + len(attributes_bin)
		dict_offset           = list_offset + len(list_items_bin)
		proto_offset          = dict_offset + len(dict_items_bin)
		proto_children_offset = proto_offset

		if proto_parent is not None:
			proto_children_offset += self.ref_word.size

		value_offset = proto_offset + len(proto_bin)

		o_module_bin = o_module.encode('utf-8')
		o_module_bin = o_module_bin[:128]
		o_module_bin = o_module_bin.ljust(128, b'\0')

		header_bin = self.header_word.pack(
			list_offset,
			dict_offset,
			proto_offset,
			proto_children_offset,
			value_offset,
			o_module_bin,
		)

		record = b''.join((
			header_bin,
			attributes_bin,
			list_items_bin,
			dict_items_bin,
			proto_bin,
			value_bin,
		))

		return record

	# Unpack attributes section from `(S32, Q)*`
	# ----------------------------------------------------------------------
	def _unpack_attributes(self, data):
		attributes = {}

		if len(data) % self.attribute_word.size != 0:
			raise ValueError('Store attributes section has invalid size')

		for key_bin, ref in self.attribute_word.iter_unpack(data):
			key = key_bin.rstrip(b'\0').decode('utf-8')
			attributes[key] = ref

		return attributes

	# Unpack list section from `Q*`
	# ----------------------------------------------------------------------
	def _unpack_list(self, data):
		items = []

		if len(data) % self.ref_word.size != 0:
			raise ValueError('Store list section has invalid size')

		for (ref,) in self.ref_word.iter_unpack(data):
			items.append(ref)

		return items

	# Unpack dict section from `(Q, Q)*`
	# ----------------------------------------------------------------------
	def _unpack_dict(self, data):
		items = {}

		if len(data) % self.dict_item_word.size != 0:
			raise ValueError('Store dict section has invalid size')

		for key_ref, value_ref in self.dict_item_word.iter_unpack(data):
			items[key_ref] = value_ref

		return items

	# Unpack proto section from `Q*`
	# ----------------------------------------------------------------------
	def _unpack_proto(self, parent_data, children_data):
		proto_parent   = None
		proto_children = []

		if len(parent_data) == self.ref_word.size:
			(proto_parent,) = self.ref_word.unpack(parent_data)
		elif len(parent_data) != 0:
			raise ValueError('Store proto parent section has invalid size')

		proto_children = self._unpack_list(children_data)

		return proto_parent, proto_children

	# Unpack full record into all sections
	# ----------------------------------------------------------------------
	def _unpack(self, record):
		view           = memoryview(record)
		header_size    = self.header_word.size
		o_module       = ''
		attributes     = {}
		list_items     = []
		dict_items     = {}
		proto_parent   = None
		proto_children = []
		value          = b''

		if len(view) < header_size:
			raise ValueError('Store record is too small to contain header')

		(
			list_offset,
			dict_offset,
			proto_offset,
			proto_children_offset,
			value_offset,
			o_module_bin,
		) = self.header_word.unpack_from(view, 0)

		if not (
			header_size <= list_offset <= dict_offset <= proto_offset <= proto_children_offset <= value_offset <= len(view)
		):
			raise ValueError('Store record has invalid section offsets')

		o_module       = o_module_bin.rstrip(b'\0').decode('utf-8')
		attributes     = self._unpack_attributes(view[header_size:list_offset])
		list_items     = self._unpack_list(view[list_offset:dict_offset])
		dict_items     = self._unpack_dict(view[dict_offset:proto_offset])
		proto_parent, proto_children = self._unpack_proto(
			view[proto_offset:proto_children_offset],
			view[proto_children_offset:value_offset],
		)
		value = bytes(view[value_offset:])

		return (
			o_module,
			attributes,
			list_items,
			dict_items,
			proto_parent,
			proto_children,
			value,
		)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	def exists(self, id):
		path = self._get_path(id)
		return os.path.exists(path)

	# Create empty record file and return its id
	# ----------------------------------------------------------------------
	def create(self):
		id   = self._get_new_id()
		path = self._get_path(id)

		with open(path, 'wb') as f:
			f.write(b'')

		return id

	# Read full record from disk and unpack it
	# ----------------------------------------------------------------------
	def read(self, id):
		path   = self._get_path(id)
		record = b''

		with open(path, 'rb') as f:
			record = f.read()

		return self._unpack(record)

	# Write full record to disk
	# ----------------------------------------------------------------------
	def write(
		self,
		id,
		*,
		o_module,
		attributes     = (),
		list_items     = (),
		dict_items     = (),
		proto_parent   = None,
		proto_children = (),
		value          = None,
	):
		path   = self._get_path(id)
		record = self._pack(
			o_module       = o_module,
			attributes     = attributes,
			list_items     = list_items,
			dict_items     = dict_items,
			proto_parent   = proto_parent,
			proto_children = proto_children,
			value          = value,
		)

		with open(path, 'wb') as f:
			f.write(record)

	# Delete record file from disk
	# ----------------------------------------------------------------------
	def delete(self, id):
		path = self._get_path(id)

		if os.path.exists(path):
			os.remove(path)