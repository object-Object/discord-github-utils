from pathlib import Path
from typing import Any


def fullname(cls: type):
    return f"{cls.__module__}.{cls.__qualname__}"


def iter_modules(parent: Any, skip_internal: bool = False):
    for filename in parent.__loader__.get_resource_reader().contents():
        path = Path(filename)
        if (
            path.suffix != ".py"
            or path.stem in {"__init__", "__main__"}
            or (skip_internal and path.stem.startswith("_"))
        ):
            continue
        yield f"{parent.__name__}.{path.stem}"
