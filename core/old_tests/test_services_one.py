import hashlib

import o


class TestServicesOne(o.Test):

	@classmethod
	def _type_id(cls, name):
		return int.from_bytes(hashlib.sha256(name.encode('utf-8')).digest()[:4], 'little')

	@classmethod
	def test_define_creates_consistent_service_state(cls):
		name = 'test_services_one_define_int64'
		type_id = cls._type_id(name)

		o.services.One.undefine(name)
		o.services.One.define(name, type_id, 'q')

		assert o.services.One.ids[name] == type_id
		assert o.services.One.names[type_id] == name
		assert type_id in o.services.One.words
		assert type_id in o.services.One.files
		assert type_id in o.services.One.free

		o.services.One.undefine(name)

	@classmethod
	def test_write_read_delete_and_free_slot_reuse(cls):
		name = 'test_services_one_rw_int64'
		type_id = cls._type_id(name)

		o.services.One.undefine(name)
		o.services.One.define(name, type_id, 'q')

		first_id = o.services.One.write(type_id, None, 11)
		second_id = o.services.One.write(type_id, None, 22)

		assert o.services.One.read(type_id, first_id) == 11
		assert o.services.One.read(type_id, second_id) == 22

		assert o.services.One.delete(type_id, first_id) == True
		assert o.services.One.delete(type_id, first_id) == False
		assert first_id in o.services.One.free[type_id]

		reused_id = o.services.One.write(type_id, None, 33)

		assert reused_id == first_id
		assert o.services.One.read(type_id, reused_id) == 33

		o.services.One.undefine(name)

	@classmethod
	def test_commit_preserves_readability(cls):
		name = 'test_services_one_commit_int64'
		type_id = cls._type_id(name)

		o.services.One.undefine(name)
		o.services.One.define(name, type_id, 'q')

		instance_id = o.services.One.write(type_id, None, 44)
		o.services.One.commit()

		assert o.services.One.read(type_id, instance_id) == 44

		o.services.One.undefine(name)


if __name__ == '__main__':
	TestServicesOne.run()
