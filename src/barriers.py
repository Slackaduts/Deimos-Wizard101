import time
from typing import Optional


class TimedBarrier:
    def __init__(self, cooldown = 5.0):
        self._tickets: list[int] = []
        self._next_id = 0
        self._cooldown_start = time.time()
        self._cooldown = cooldown

    def fetch(self) -> int:
        result = self._next_id
        self._next_id += 1
        self._tickets.append(result)
        return result

    def submit(self, ticket: int, skip_cooldown=False):
        self._tickets.remove(ticket)
        if not skip_cooldown:
            # For tasks that are unambiguously done. Another task may still add cooldown.
            self._cooldown_start = time.time()

    def block_cooldown(self):
        self._cooldown_start = time.time()

    def is_blocked(self):
        return len(self._tickets) > 0 or time.time() - self._cooldown_start < self._cooldown

    def is_free(self):
        return not self.is_blocked()


class SingleWriteValue[T]:
    def __init__(self):
        self._value: Optional[T] = None

    def filled(self) -> bool:
        return self._value is not None

    def reset(self):
        self._value = None

    def write(self, value: T):
        if self._value is not None:
            raise RuntimeError("Tried writing to a filled single write value")
        self._value = value

    def read(self) -> T:
        if self._value is None:
            raise RuntimeError("Tried reading an unfilled single write value")
        return self._value

    def consume(self) -> T:
        result = self.read()
        self.reset()
        return result