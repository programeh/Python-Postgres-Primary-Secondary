import logging
import requests
import json
from datetime import datetime

class HTTPLogHandler(logging.Handler):
    def __init__(self, endpoint_url):
        super().__init__()
        self.endpoint_url = endpoint_url

    def emit(self, record):
        try:
            log_entry = self.format(record)
            headers = {'Content-Type': 'application/json'}
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            response = requests.post(
                self.endpoint_url,
                data=json.dumps({"log": log_entry,"timestamp": timestamp}),
                headers=headers
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send log: {e}")


def get_logger(endpoint_url, level=logging.DEBUG):
    """Factory function to create and return a logger."""
    logger = logging.getLogger("http_logger")
    logger.setLevel(level)

    http_handler = HTTPLogHandler(endpoint_url)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    http_handler.setFormatter(formatter)

    logger.addHandler(http_handler)
    return logger