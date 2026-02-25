# ======================================================================
# In-memory canonical form: torch.float32 Tensor on CPU
# ======================================================================

import torch
import numpy as np

import o


class Vector(o.CustomType):

	# Serialize vector to binary blob
	# ----------------------------------------------------------------------
	@classmethod
	def serialize(cls, vector) -> bytes:
		blob = None

		if vector is not None:
			if isinstance(vector, torch.Tensor):
				arr = vector.detach().to(torch.float32).cpu().numpy()
			elif isinstance(vector, np.ndarray):
				arr = vector.astype(np.float32)
			else:
				arr = np.asarray(vector, dtype=np.float32)
			blob = arr.tobytes()

		return blob

	# Serialize binary blob to torch tensor
	# ----------------------------------------------------------------------
	@classmethod
	def deserialize(cls, blob) -> torch.Tensor | None:
		vector = None

		if blob is not None:
			if isinstance(blob, torch.Tensor):
				vector = blob.to(torch.float32)
			elif isinstance(blob, np.ndarray):
				vector = torch.from_numpy(blob.astype(np.float32))
			elif isinstance(blob, (bytes, bytearray, memoryview)):
				arr = np.frombuffer(blob, dtype=np.float32)
				vector = torch.from_numpy(arr)
			else:
				vector = torch.as_tensor(blob, dtype=torch.float32)

		return vector