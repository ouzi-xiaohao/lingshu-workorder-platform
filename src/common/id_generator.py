import time
from uuid import uuid4


def new_order_no() -> str:
    return f"WO-{time.strftime('%Y%m%d')}-{uuid4().hex[:12].upper()}"
