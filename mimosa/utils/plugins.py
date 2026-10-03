import os

# built-in plugins live in <project root>/plugins/<kind>
PLUGIN_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "plugins")


def builtin_folder(kind):
    return os.path.join(PLUGIN_ROOT, kind)


def module_names(folder):
    """ Names of the plugin modules (.py files) in a folder, skipping __pycache__ and the like """
    return [name[:-3] for name in sorted(os.listdir(folder)) if name.endswith(".py") and not name.startswith("_")]
