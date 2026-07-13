import logging
from collections import deque
from datetime import datetime

# Global log history buffer
log_history = deque(maxlen=200)

class WebsocketLogHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = self.format(record)
            log_history.append({
                "timestamp": datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3],
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name
            })
        except Exception:
            pass

logger = logging.getLogger("robotics_framework")
logger.setLevel(logging.INFO)

# Setup standard formatting
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", "%H:%M:%S")

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Custom websocket/buffer handler
ws_handler = WebsocketLogHandler()
ws_handler.setFormatter(formatter)
logger.addHandler(ws_handler)
