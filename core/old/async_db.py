import asyncio

import o


class AsyncDb(o.Service):

	def __getattr__(self, name):
		fn = getattr(o.Db, name)
		if not callable(fn):
			return fn

		async def wrapper(*args, **kwargs):
			return await asyncio.to_thread(fn, *args, **kwargs)

		return wrapper

	def initialize(self): pass

