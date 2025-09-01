from typing import Awaitable, Callable

type AsyncCallable[**P, R] = Callable[P, Awaitable[R]]
