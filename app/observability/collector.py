from contextvars import ContextVar

steps_ctx: ContextVar[list | None] = ContextVar(
    "steps_ctx",
    default=None
)


def init_steps():
    steps_ctx.set([])


def add_step(step: dict):

    steps = steps_ctx.get()

    if steps is None:
        steps = []

    steps.append(step)

    steps_ctx.set(steps)


def get_steps():

    steps = steps_ctx.get()

    return steps or []

def update_step_metadata(
    step_name: str,
    trace_metadata: dict
):

    steps = get_steps()

    for step in reversed(steps):

        if step["name"] == step_name:

            step["trace_metadata"] = trace_metadata

            break

    steps_ctx.set(steps)