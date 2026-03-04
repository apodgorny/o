import inspect, hashlib

import o


class TestInt(o.Test):

	@classmethod
	def test_basic(cls):
		x = o.Int(10)
		assert int(x) == 10
		x.__write__(20)
		assert int(x) == 20

	@classmethod
	def test_isolation(cls):
		x = o.Int(10)
		y = o.Int(20)
		assert int(x) == 10
		assert int(y) == 20

	@classmethod
	def test_cast_consistency(cls):
		x = o.Int(15)
		assert int(x) == x.__cast_out__()

	@classmethod
	def test_non_mutating_method(cls):
		x = o.Int(8)
		assert x.bit_length() == 4
		assert int(x) == 8

	@classmethod
	def test_operator(cls):
		x = o.Int(8)
		assert (x + 2) == 10
		assert int(x) == 8

	@classmethod
	def test_delete(cls):
		x = o.Int(3)
		x.__delete__()
		try:
			int(x)
			assert False
		except ValueError:
			pass

	@classmethod
	def test_rewrite_after_delete(cls):
		x = o.Int(5)
		x.__delete__()
		x.__write__(12)
		assert int(x) == 12

	@classmethod
	def test_define_undefine_stability(cls):
		name = 'temp_type'
		word = 'q'

		type_id = int.from_bytes(hashlib.sha256(name.encode('utf-8')).digest()[:4], 'little')

		t1 = o.services.One.define(name, type_id, word)
		o.services.One.undefine(name)
		t2 = o.services.One.define(name, type_id, word)

		assert t1 == t2, 'Type id must be deterministic and stable'
		assert t1 == type_id, 'Returned type id must match provided one'


if __name__ == '__main__':
	TestInt.run()
	print('\nAll tests passed')