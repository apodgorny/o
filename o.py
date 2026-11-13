# ==============================================================================
# ONTOLOGY LIBRARY
# ==============================================================================
# Publish the ontology namespace without starting persistent storage on import.
# ==============================================================================

import a


o = a.extend('o')

o.DATA_DIR    = None
o.MEMORY_SIZE = 1073741824
o.TREE_MODE   = False

# Each ontology starts explicitly; fork() only selects its isolated world.
# sync=True flushes LMDB commits; multiprocess=True enables IPC (off by default).
o.start = o.services.Ontology.start
o.fork  = o.services.Ontology.fork
