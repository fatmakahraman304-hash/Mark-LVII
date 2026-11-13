"""Safe adapter interfaces. No arbitrary command execution or OS privilege escalation."""
from __future__ import annotations
from abc import ABC, abstractmethod
from command_protocol import Command, CommandResult, ResultCode
from device_registry import DeviceRegistry

class DeviceAdapter(ABC):
    @property
    @abstractmethod
    def supported_actions(self) -> frozenset[str]:
        ...

    @abstractmethod
    def execute(self, command: Command) -> CommandResult:
        ...

class ReadOnlyStatusAdapter(DeviceAdapter):
    """Only locally supplied status; does not collect or expose system secrets."""
    def __init__(self, status_provider):
        self._provider = status_provider

    @property
    def supported_actions(self) -> frozenset[str]:
        return frozenset({"status.read"})

    def execute(self, command: Command) -> CommandResult:
        if command.action != "status.read":
            return CommandResult(command.command_id, ResultCode.UNSUPPORTED, "Action unsupported")
        try:
            status = self._provider()
            if not isinstance(status, str):
                raise ValueError("Status must be text")
            return CommandResult(command.command_id, ResultCode.OK, status[:256])
        except Exception:
            return CommandResult(command.command_id, ResultCode.FAILED, "Status unavailable")

class CommandDispatcher:
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry
        self.adapters: dict[str, DeviceAdapter] = {}

    def attach(self, device_id: str, adapter: DeviceAdapter) -> None:
        if self.registry.get(device_id) is None:
            raise ValueError("Unknown device")
        self.adapters[device_id] = adapter

    def dispatch(self, command: Command) -> CommandResult:
        check = self.registry.check(command)
        if check.code != ResultCode.OK:
            return check
        adapter = self.adapters.get(command.device_id)
        if adapter is None or command.action not in adapter.supported_actions:
            return CommandResult(command.command_id, ResultCode.UNSUPPORTED, "No verified adapter")
        return adapter.execute(command)
