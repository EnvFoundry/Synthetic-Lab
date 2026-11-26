"""Domain workers execute queued experiments outside database write transactions."""

import threading
import uuid

from .models import available


class Worker:
    def __init__(
        self,
        lab,
        *,
        models=None,
        worker_id=None,
        lease_seconds=300.0,
        poll_seconds=0.1,
    ):
        self.lab = lab
        self.models = tuple(available() if models is None else models)
        unknown = sorted(set(self.models) - set(available()))
        if unknown:
            raise ValueError(f"Worker cannot load laboratories {unknown}")
        self.id = worker_id or "worker-" + uuid.uuid4().hex
        self.lease_seconds = float(lease_seconds)
        self.poll_seconds = float(poll_seconds)
        if self.lease_seconds <= 0 or self.poll_seconds < 0:
            raise ValueError("lease_seconds must be positive and poll_seconds nonnegative")

    def run_once(self):
        return self.lab.run_next(
            worker_id=self.id,
            models=self.models,
            lease=self.lease_seconds,
        )

    def serve(self, stop=None):
        stop = threading.Event() if stop is None else stop
        completed = 0
        while not stop.is_set():
            result = self.run_once()
            if result is None:
                stop.wait(self.poll_seconds)
            else:
                completed += 1
        return completed
