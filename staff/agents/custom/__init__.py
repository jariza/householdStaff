# Dynamically discovers and exposes functions from 'customs' agents.
# From each, only the class that has process method will be imported.

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
import re

logger = logging.getLogger(__name__)

__all__ = ["CUSTOM_AGENTS"]

CUSTOM_AGENTS = {}

# Get the absolute path of the 'customs' directory
_pkg_dir = Path(__file__).parent

for _, _module_name, _ in pkgutil.iter_modules([str(_pkg_dir)]):
    # Ignore private or dunder files (e.g., __init__.py, _helper.py)
    if _module_name.startswith('_'):
        continue

    try:
        # Dynamically import the module
        _module = importlib.import_module(f".{_module_name}", package=__name__)

        # Import only the local classes that have a process method
        matching_classes = []
        for name, obj in inspect.getmembers(_module, inspect.isclass):
            if obj.__module__ == _module.__name__ and hasattr(obj, "process") and callable(getattr(obj, "process")):
                matching_classes.append((name, obj))

        # Only one class will be imported per module
        if len(matching_classes) == 0:
            logger.warning(f"None of the classes in {_module_name} has a process method.")
        elif len(matching_classes) > 1:
            class_names = [name for name, _ in matching_classes]
            raise ValueError(f"There is more than one class with process method in {_module_name}.")
        else:
            class_name, class_obj = matching_classes[0]
            globals()[class_name] = class_obj
            __all__.append(class_name)
            agent_name = re.sub(r'agent', '', class_name, flags=re.IGNORECASE).lower()
            CUSTOM_AGENTS[agent_name] = class_obj

    except Exception as e:
        # Prevent a broken custom script from crashing the entire application
        logging.error(f"Failed to load custom module '{_module_name}': {e}")