# ==============================================================================
# ONTOLOGY LIBRARY
# ==============================================================================
# Publish the ontology namespace without starting persistent storage on import.
# ==============================================================================

import a


o = a.extend('o')

o.DATA_DIR    = '__memory__'
o.MEMORY_SIZE = 1073741824

# Preserve the explicit creation/start boundary for existing applications.
o.start = o.services.Ontology.start
