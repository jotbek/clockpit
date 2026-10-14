"""Load one animation at a time and release both package and cache references."""
import gc
import sys


def create_module(module_name, class_name, xres, yres):
    gc.collect()
    module = __import__(module_name, None, None, (class_name,))
    return getattr(module, class_name)(xres, yres)


def unload_module(module_name):
    if module_name in sys.modules:
        del sys.modules[module_name]
    parts = module_name.rsplit('.', 1)
    if len(parts) == 2:
        package = sys.modules.get(parts[0])
        if package is not None and hasattr(package, parts[1]):
            delattr(package, parts[1])
