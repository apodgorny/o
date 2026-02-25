import sys
from collections           import defaultdict

from whitelabel.wl         import WL


o = WL.define(
	'o',
	__file__,

	types                    = None,                 # class_name -> class

	__cache_by_id__          = defaultdict(dict),  # class_name -> id          -> instance
	__cache_by_key__         = defaultdict(dict),  # class_name -> key         -> instance
	__cache_by_instance_id__ = defaultdict(dict)   # class_name -> instance_id -> instance
)

o.types = o.Conf
