import o2


class Disk(o2.Service):
	def size_on_disk(fullname):
		parts = fullname.split('_')
		name = parts.pop(0)
		return product([int(p) for p in parts])


	def set_type(self, type):
		pass
	

	def get(self, id, type):


