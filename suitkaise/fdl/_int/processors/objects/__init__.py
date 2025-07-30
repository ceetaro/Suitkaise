# processors/objects/__init__.py

# Import all object processors to ensure they are registered
from . import time_objects
from . import spinner_objects
from . import type_objects
# Tables and progress bars are standalone, not processed through object system