"""A claim on "one manual run at a time" that a handler takes before it answers."""


class RunSlot:
    """Check and claim happen with no await between them, so two requests can't both win."""

    def __init__(self) -> None:
        self._held = False

    @property
    def held(self) -> bool:
        return self._held

    def try_reserve(self) -> bool:
        if self._held:
            return False
        self._held = True
        return True

    def release(self) -> None:
        self._held = False
