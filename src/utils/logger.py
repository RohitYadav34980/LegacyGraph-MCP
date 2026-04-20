import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

class ISTFormatter(logging.Formatter):
    """Custom Formatter to enforce Indian Standard Time (IST) in logs."""
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC"))
        return dt.astimezone(ZoneInfo("Asia/Kolkata")).timetuple()

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Kolkata"))
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

# Initialize the main MCP Server logger
logger = logging.getLogger("mcp_server")
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent double logging if root catches it

# Create Custom Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Set clean, privacy-aware format: [IST Time] LEVEL [Source] Message
log_format = "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
formatter = ISTFormatter(fmt=log_format, datefmt="%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(formatter)

# Add handler to our logger
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(console_handler)

# Apply this clean format to Uvicorn and FastMCP so HTTP hits are clean 
# but still visible, as requested by the user.
for foreign_logger_name in ["uvicorn.access", "uvicorn.error", "mcp.server.lowlevel.server", "mcp.server.streamable_http_manager"]:
    fl = logging.getLogger(foreign_logger_name)
    fl.setLevel(logging.INFO) # Keep them visible
    if fl.hasHandlers():
        fl.handlers.clear()
    fl.addHandler(console_handler)
    fl.propagate = False
