# ==============================================================================
# ONTOLOGY LIBRARY
# ==============================================================================
# Publish the ontology namespace without starting persistent storage on import.
# ==============================================================================

import a


o = a.extend('o')

o.DATA_DIR    = '__memory__'
o.MEMORY_SIZE = 1073741824

# Explicit startup: o.start(path=None, sync=False).
# sync=True asks LMDB to flush each commit; False favors throughput over durability.
o.start = o.services.Ontology.start
