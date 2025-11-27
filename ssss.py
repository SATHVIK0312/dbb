# ==================== STRUCTURED LOGGING – FINAL SINGLE-FILE VERSION ====================

import json
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    ACTION = "ACTION"

class LogCategory(str, Enum):
    INITIALIZATION = "INIT"
    PLAN_BUILDING = "PLAN"
    SEARCH = "SEARCH"
    GENERATION = "GENERATION"
    EXECUTION = "EXECUTION"
    HEALING = "HEALING"
    STORAGE = "STORAGE"
    CLEANUP = "CLEANUP"

@dataclass
class StructuredLog:
    timestamp: str
    level: str
    category: str
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_readable(self):
        parts = [f"[{self.timestamp}]", f"[{self.level}]", f"[{self.category}]", self.message]
        if self.code:
            parts.append(f"(Code: {self.code})")
        if self.duration_ms is not None:
            parts.append(f"({self.duration_ms:.1f}ms)")
        return " ".join(parts)

class StructuredLogger:
    """Fully working SQLite-compatible structured logger"""

    def __init__(self, testcase_id: str):     # ✅ FIXED CONSTRUCTOR
        self.testcase_id = testcase_id
        self.logs: List[StructuredLog] = []
        self.start_time = datetime.now()

    def _add(self, level: LogLevel, category: LogCategory, message: str,
             code=None, details=None, duration_ms=None):

        entry = StructuredLog(
            timestamp=datetime.now().isoformat(timespec="milliseconds"),
            level=level.value,
            category=category.value,
            message=message,
            code=code,
            details=details,
            duration_ms=duration_ms
        )

        self.logs.append(entry)

        # send to console
        level_map = {
            LogLevel.DEBUG: logger.debug,
            LogLevel.INFO: logger.info,
            LogLevel.WARNING: logger.warning,
            LogLevel.ERROR: logger.error,
            LogLevel.SUCCESS: logger.info,
            LogLevel.ACTION: logger.info,
        }
        level_map.get(level, logger.info)(entry.to_readable())

    def info(self, cat, msg, code=None, details=None):
        self._add(LogLevel.INFO, cat, msg, code, details)

    def success(self, cat, msg, code=None, details=None):
        self._add(LogLevel.SUCCESS, cat, msg, code, details)

    def error(self, cat, msg, code=None, details=None):
        self._add(LogLevel.ERROR, cat, msg, code, details)

    def action(self, name, status, duration_ms=None, details=None):
        self._add(LogLevel.ACTION, LogCategory.EXECUTION,
                  f"Action '{name}' → {status}", code=name,
                  duration_ms=duration_ms, details=details)

    def step(self, step_name, step_num, status, duration_ms, error=None, screenshot=None):
        details = {"step_number": step_num, "status": status, "duration_ms": duration_ms}
        if error: details["error"] = error
        if screenshot: details["screenshot"] = screenshot

        level = LogLevel.SUCCESS if status == "PASS" else LogLevel.ERROR

        self._add(level, LogCategory.EXECUTION,
                  f"Step {step_num}: {step_name}",
                  code=f"STEP_{step_num:03d}",
                  details=details)

    def get_readable_logs(self):
        return "\n".join(log.to_readable() for log in self.logs)

    def get_json_logs(self):
        return json.dumps([log.to_dict() for log in self.logs], indent=2)

    def get_summary(self):
        total_time = (datetime.now() - self.start_time).total_seconds() * 1000
        errors = sum(1 for l in self.logs if l.level == LogLevel.ERROR.value)
        return {
            "testcase_id": self.testcase_id,
            "total_logs": len(self.logs),
            "total_time_ms": round(total_time, 1),
            "errors": errors,
            "status": "SUCCESS" if errors == 0 else "FAILED"
        }
