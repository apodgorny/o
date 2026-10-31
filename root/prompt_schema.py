import o


class PromptSchema(o.JsonSchema):

	# Omit fields intended for application state rather than LLM output.
	# ----------------------------------------------------------------------
	@classmethod
	def _get_fields(cls, t_cls):
		fields = super()._get_fields(t_cls)
		return {
			name: field
			for name, field in fields.items()
			if getattr(field, 'prompt', True)
		}
