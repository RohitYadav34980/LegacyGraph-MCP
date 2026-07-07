import logging
import sys
import time
from datetime import datetime, timezone, timedelta, tzinfo
from typing import Optional

# ZoneInfo requires 'tzdata' on Windows; fall back to fixed offsets if unavailable
_TZ_UTC: tzinfo
_TZ_IST: tzinfo
try:
    from zoneinfo import ZoneInfo
    _TZ_UTC = ZoneInfo("UTC")
    _TZ_IST = ZoneInfo("Asia/Kolkata")
except (ImportError, KeyError):
    _TZ_UTC = timezone.utc
    _TZ_IST = timezone(timedelta(hours=5, minutes=30))

class ISTFormatter(logging.Formatter):
    """Custom Formatter to enforce Indian Standard Time (IST) in logs."""
    def converter(self, timestamp: Optional[float]) -> time.struct_time:
        dt = datetime.fromtimestamp(timestamp or 0.0, tz=_TZ_UTC)
        return dt.astimezone(_TZ_IST).timetuple()

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=_TZ_UTC).astimezone(_TZ_IST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

# Initialize the main MCP Server logger
logger = logging.getLogger("mcp_server")
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent double logging if root catches it

# Create Custom Console Handler.
# IMPORTANT: logs must go to stderr — in stdio transport mode stdout carries
# the JSON-RPC protocol stream, and any log line written there corrupts it.
console_handler = logging.StreamHandler(sys.stderr)
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
for foreign_logger_name in [
    "uvicorn.access",
    "fastmcp",
    "FastMCP",
    "mcp.server.lowlevel.server",
    "mcp.server.streamable_http_manager",
]:
    fl = logging.getLogger(foreign_logger_name)
    fl.setLevel(logging.INFO) # Keep them visible
    if fl.hasHandlers():
        fl.handlers.clear()
    fl.addHandler(console_handler)
    fl.propagate = False
