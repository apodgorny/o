import o


class TestServicesDefinition(o.Test):

	@classmethod
	def test_field_serialize_contract(cls):
		required = o.F(name='age', type=int, description='years')
		optional = o.F(name='name', type=str, description=None, default='alex')

		assert required.serialize() == {
			'name': 'age',
			'type': 'int',
			'description': 'years',
			'default': '__undefined__',
			'is_optional': False,
		}

		assert optional.serialize() == {
			'name': 'name',
			'type': 'str',
			'description': None,
			'default': 'alex',
			'is_optional': True,
		}

	@classmethod
	def test_type_serialize_atomic_contract(cls):
		Token = o.T.define('TestServicesDefinitionToken', str)

		assert Token.serialize() == {
			'type_name': 'TestServicesDefinitionToken',
			'annotation': 'str',
			'fields': [],
			'o_module': 'o.T.TestServicesDefinitionToken',
		}

	@classmethod
	def test_definition_count_methods_and_get(cls):
		Token = o.T.define('TestServicesDefinitionCountToken', str)
		type_id = Token.__type_id__

		o.services.Definition.define(Token)

		assert o.services.Definition.get(type_id) is Token
		assert o.services.Definition.get_count(type_id) == 0
		assert o.services.Definition.inc_count(type_id) == 1
		assert o.services.Definition.get_count(type_id) == 1
		assert o.services.Definition.dec_count(type_id) == 0
		assert o.services.Definition.get_count(type_id) == 0

	@classmethod
	def test_definition_persists_object_spec_shape(cls):
		User = o.T.define('TestServicesDefinitionUser', name=str, age=int)
		type_id = User.__type_id__

		o.services.Definition.define(User)
		spec = o.services.Definition._read_definition(type_id)

		assert spec['type_name'] == 'TestServicesDefinitionUser'
		assert spec['annotation'] is None
		assert spec['o_module'] == 'o.T.TestServicesDefinitionUser'
		assert {field['name'] for field in spec['fields']} == {'name', 'age'}


if __name__ == '__main__':
	TestServicesDefinition.run()
