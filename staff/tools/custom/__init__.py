# Dynamically discovers and exposes functions from 'customs' tools.
# Only imports functions matching their parent file name (e.g., custom_tool() from custom_tool.py).

import importlib
import logging
import pkgutil
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = []

# Get the absolute path of the 'customs' directory
_pkg_dir = Path(__file__).parent

for _, _module_name, _ in pkgutil.iter_modules([str(_pkg_dir)]):
    # Ignore private or dunder files (e.g., __init__.py, _helper.py)
    if _module_name.startswith('_'):
        continue

    try:
        # Dynamically import the module
        _module = importlib.import_module(f".{_module_name}", package=__name__)
        
        # Look for an attribute (function/class) matching the file name
        _target = getattr(_module, _module_name, None)

        # Import ONLY if the function/class with the same name exists
        if _target is not None:
            globals()[_module_name] = _target
            __all__.append(_module_name)

    except Exception as e:
        # Prevent a broken custom script from crashing the entire application
        logger.error(f"Failed to load custom module '{_module_name}': {e}")