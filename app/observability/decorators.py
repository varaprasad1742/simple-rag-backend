import time

from functools import wraps

from app.core.request_context import (
    trace_id_ctx,
    user_id_ctx
)

from app.observability.collector import (
    add_step
)


def observe(name=None):

    def decorator(func):

        operation = (
            name or func.__name__
        )

        @wraps(func)
        async def wrapper(
            *args,
            **kwargs
        ):

            trace_id = (
                trace_id_ctx.get()
            )

            user_id = (
                user_id_ctx.get()
            )

            start = (
                time.perf_counter()
            )

            try:

                result = await func(
                    *args,
                    **kwargs
                )

                duration = (
                    time.perf_counter()
                    - start
                )

                add_step(
                    {
                        "trace_id":
                        trace_id,

                        "user_id":
                        user_id,

                        "name":
                        operation,

                        "duration":
                        duration,

                        "status":
                        "success",
                        "trace_metadata": {}
                    }
                )

                return result

            except Exception:

                duration = (
                    time.perf_counter()
                    - start
                )

                add_step(
                    {
                        "trace_id":
                        trace_id,

                        "user_id":
                        user_id,

                        "name":
                        operation,

                        "duration":
                        duration,

                        "status":
                        "error",
                         "trace_metadata": {}
                    }
                )

                raise

        return wrapper

    return decorator