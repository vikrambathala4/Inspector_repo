import logging
import sys

class CustomFormatter(logging.Formatter):
    def format(self, record):
        log_time = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        log_level = record.levelname.lower()
        log_msg = record.getMessage()
        log_file = f'{record.filename}:{record.lineno}'
        s = f'time="{log_time}" level={log_level} msg="{log_msg}" file="{log_file}"'
        return s
