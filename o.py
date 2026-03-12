import sys
from collections   import defaultdict

from whitelabel.wl import WL


def initialize(o):
	o.F
	for module in o:
		print(module.name)
		module.load()


o = WL.define(
	'o',
	__file__,

	__types_by_id__   = {},  # type_id    -> type_class
	__types_by_name__ = {},  # type_o_module -> type_class
	__cast_map__      = {},  # Annotation -> o.T subclass

	on_initialize = initialize
)