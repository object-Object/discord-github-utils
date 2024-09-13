from importlib import resources


def get_resource(name: str):
    files = resources.files()
    return files / name


def load_resource(name: str, encoding: str = "utf-8"):
    return get_resource(name).read_text(encoding)
