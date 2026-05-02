import o


class TempClasses(o.Service):

	# Mark temp class as protected
	# ----------------------------------------------------------------------
	def set(self, proto):
		o.services.Memory.set(f'temp:{proto}', True)

	# Remove temp class protection
	# ----------------------------------------------------------------------
	def unset(self, proto):
		o.services.Memory.unset(f'temp:{proto}')

	# Delete all remaining temp classes
	# ----------------------------------------------------------------------
	def clear(self):
		temp_protos = []

		with o.services.Memory.batch() as batch:
			for key in batch.keys('temp:'):
				temp_protos.append(key[len('temp:'):])

		for proto in temp_protos:
			o.get(proto).delete()
			self.unset(proto)
