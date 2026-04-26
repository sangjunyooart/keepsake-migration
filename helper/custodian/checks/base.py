from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CheckResult:
    check_name: str
    severity: Severity
    summary: str
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    auto_action: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "severity": self.severity.value,
            "summary": self.summary,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "auto_action": self.auto_action,
        }


class Check(ABC):
    name: str

    def __init__(self, mac_root, config: dict, lens_configs: dict):
        self.mac_root = mac_root
        self.config = config
        self.lens_configs = lens_configs

    @abstractmethod
    def run(self) -> CheckResult:
        ...
