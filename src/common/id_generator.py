import threading
import time


class SnowflakeGenerator:
    EPOCH = 1_700_000_000_000

    def __init__(self, worker_id: int = 1):
        if not 0 <= worker_id <= 1023:
            raise ValueError("worker_id must be between 0 and 1023")
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

    def next_id(self) -> int:
        with self.lock:
            timestamp = int(time.time() * 1000)
            if timestamp < self.last_timestamp:
                raise RuntimeError("system clock moved backwards")
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & 4095
                while self.sequence == 0 and timestamp <= self.last_timestamp:
                    timestamp = int(time.time() * 1000)
            else:
                self.sequence = 0
            self.last_timestamp = timestamp
            return ((timestamp - self.EPOCH) << 22) | (self.worker_id << 12) | self.sequence


generator = SnowflakeGenerator()


def new_order_no() -> str:
    return f"WO-{time.strftime('%Y%m%d')}-{generator.next_id() % 1_000_000:06d}"
