import o


class Garbage(o.Service):

	# Initialize service
	# ----------------------------------------------------------------------
	def initialize(self):
		memory = o.services.Memory

		self.refcounts      = memory.zone('garbage/refcounts/')
		self.instancecounts = memory.zone('garbage/instancecounts/')
		self.garbage        = memory.zone('garbage/items/')

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
			for dependant in instance.__dependants__():
				self._on_instance_link(dependant)

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
				for dependant in instance.__dependants__():
					self._on_instance_unlink(dependant)
		else:
			self.refcounts.set(instance.id, count)

	# Register class birth
	# ----------------------------------------------------------------------
	def on_class_create(self, cls):
		if cls.__is_temp__:
			with o.services.Memory.write():
				self.garbage.set(cls.id, cls.__proto__)

	# Register instance birth
	# ----------------------------------------------------------------------
	def on_instance_create(self, instance):
		cls = instance.__class__

		if cls.__is_temp__:
			with o.services.Memory.write():
				cls_id = cls.id
				count  = self.instancecounts.get(cls_id, 0) + 1

				if count == 1:
					self.garbage.unset(cls_id)

				self.instancecounts.set(cls_id, count)

	# Register instance death
	# ----------------------------------------------------------------------
	def on_instance_delete(self, instance):
		cls = instance.__class__

		if cls.__is_temp__:
			with o.services.Memory.write():
				cls_id = cls.id
				count  = self.instancecounts.get(cls_id, 0) - 1
				count  = max(count, 0)

				if count == 0:
					self.instancecounts.unset(cls_id)
					self.garbage.set(cls_id, cls.__proto__)
				else:
					self.instancecounts.set(cls_id, count)

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
