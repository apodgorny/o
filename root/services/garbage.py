import o


class Garbage(o.Service):

	# Initialize service
	# ----------------------------------------------------------------------
	def initialize(self):
		memory = o.services.Memory

		self.refcounts = memory.zone('garbage/refcounts/')
		self.garbage   = memory.zone('garbage/items/')

		self.collect()

	# Link holding edge
	# ----------------------------------------------------------------------
	def on_instance_link(self, instance):
		with o.services.Memory.write():
			self._on_instance_link(instance)

	# Link holding edge in active transaction
	# ----------------------------------------------------------------------
	def _on_instance_link(self, instance):
		old_count = self.refcounts.get(instance.id, 0)
		count     = old_count + 1

		self.refcounts.set(instance.id, count)
		self.garbage.unset(instance.id)

		if old_count == 0:
			for key, n_proto, child in instance.__dependants__():
				self._on_instance_link(child)

	# Unlink holding edge
	# ----------------------------------------------------------------------
	def on_instance_unlink(self, instance):
		with o.services.Memory.write():
			self._on_instance_unlink(instance)

	# Unlink holding edge in active transaction
	# ----------------------------------------------------------------------
	def _on_instance_unlink(self, instance):
		old_count = self.refcounts.get(instance.id, 0)
		count     = max(old_count - 1, 0)

		if count == 0:
			self.refcounts.unset(instance.id)
			self.garbage.set(instance.id, instance.__proto__)

			if old_count == 1:
				for key, n_proto, child in instance.__dependants__():
					self._on_instance_unlink(child)
		else:
			self.refcounts.set(instance.id, count)

	# Collect garbage storage
	# ----------------------------------------------------------------------
	def collect(self):
		with o.services.Memory.write():
			for id, proto in self.garbage.items():
				o.services.Memory.unset(proto)
				o.services.Memory.zone(f'{proto}.').clear()

			self.clear()

	# Clear garbage storage
	# ----------------------------------------------------------------------
	def clear(self):
		self.garbage.clear()
