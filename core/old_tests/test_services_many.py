import o


class TestServicesMany(o.Test):

	@classmethod
	def test_create_write_read_clear_and_delete(cls):
		id_ = o.services.Many.create('IQ')

		assert o.services.Many.read(id_) == []

		items = [(1, 10), (2, 20)]
		o.services.Many.write(id_, items)

		assert o.services.Many.read(id_) == items

		o.services.Many.clear(id_)

		assert o.services.Many.read(id_) == []
		assert o.services.Many.delete(id_) == True
		assert o.services.Many.delete(id_) == False

	@classmethod
	def test_write_overwrites_full_container(cls):
		id_ = o.services.Many.create('IQ')

		o.services.Many.write(id_, [(1, 10), (2, 20)])
		o.services.Many.write(id_, [(3, 30)])

		assert o.services.Many.read(id_) == [(3, 30)]

		o.services.Many.delete(id_)

	@classmethod
	def test_commit_preserves_readability(cls):
		id_ = o.services.Many.create('IQ')

		o.services.Many.write(id_, [(7, 70)])
		o.services.Many.commit()

		assert o.services.Many.read(id_) == [(7, 70)]

		o.services.Many.delete(id_)


if __name__ == '__main__':
	TestServicesMany.run()
