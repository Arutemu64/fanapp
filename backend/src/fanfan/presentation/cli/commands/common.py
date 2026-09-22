import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any


def async_command[**P, R](
    f: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[P, R]:
    """Let Click invoke an async command by running it to completion.

    Parameterised rather than a bare `Callable`: Click reads the wrapped
    function's signature to bind its options, and an unparameterised decorator
    erases that signature to Unknown — which silently switches ty off for every
    command it decorates (`dynamic-function-decorator-return`).
    """

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return asyncio.run(f(*args, **kwargs))

    return wrapper
