from pydantic import BaseModel, create_model, ConfigDict

# --------------------------------------------
# User-declared model
# --------------------------------------------
class User(BaseModel):
	name: str

	model_config = ConfigDict(extra='forbid')

# важно для v2, если модель участвует как base
User.model_rebuild()

u = User(name='Alice')

print(isinstance(u, User))     # True
print(u.__class__ is User)     # True (частный случай)

# --------------------------------------------
# Runtime-generated subclass
# --------------------------------------------
RuntimeUser = create_model(
	'RuntimeUser',
	__base__ = User
)

ru = RuntimeUser(name='Bob')

print(isinstance(ru, User))          # True  ← контракт
print(isinstance(ru, RuntimeUser))   # True
print(ru.__class__ is User)           # False
print(issubclass(RuntimeUser, User)) # True
