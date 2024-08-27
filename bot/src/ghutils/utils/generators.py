from typing import Any, Generator


def send_final[Send](generator: Generator[Any, Send, Any], value: Send):
    try:
        generator.send(value)
    except StopIteration:
        pass
    else:
        raise RuntimeError("generator unexpectedly yielded another value")
