"""In-memory registry. Pairing credentials must be verified by a separate trusted server."""
from __future__ import annotations
from dataclasses import dataclass, field
import secrets
import time
from command_protocol import Command, CommandResult, ResultCode

@dataclass
class Device:
    device_id: str
    platform: str
    capabilities: set[str] = field(default_factory=set)
    paired: bool = False
    revoked: bool = False
    online: bool = False
    last_seen: float = 0.0

class DeviceRegistry:
    def __init__(self):
        self._devices: dict[str, Device] = {}
        self._seen: dict[str, dict[str, float]] = {}

    def register(self, device: Device) -> None:
        if not device.device_id or device.device_id in self._devices:
            raise ValueError("Duplicate or empty device ID")
        self._devices[device.device_id] = device

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def authorize(self, device_id: str) -> None:
        """Call only after trusted server-side pairing has been verified."""
        device = self._devices[device_id]
        if device.revoked:
            raise PermissionError("Device revoked")
        device.paired = True

    def revoke(self, device_id: str) -> None:
        device = self._devices[device_id]
        device.revoked = True
        device.paired = False
        device.online = False
        self._seen.pop(device_id, None)

    def heartbeat(self, device_id: str) -> None:
        device = self._devices[device_id]
        if device.revoked or not device.paired:
            raise PermissionError("Not paired")
        device.online = True
        device.last_seen = time.time()

    def check(self, command: Command) -> CommandResult:
        command.validate()
        device = self.get(command.device_id)
        if not device or not device.paired or device.revoked:
            return CommandResult(command.command_id, ResultCode.DENIED, "Device not paired")
        if command.is_expired():
            return CommandResult(command.command_id, ResultCode.EXPIRED, "Command expired")
        if not device.online or time.time() - device.last_seen > 90:
            return CommandResult(command.command_id, ResultCode.OFFLINE, "Device offline")
        if command.action not in device.capabilities:
            return CommandResult(command.command_id, ResultCode.UNSUPPORTED, "Capability unavailable")
        seen = self._seen.setdefault(device.device_id, {})
        now = time.time()
        for key, expiry in list(seen.items()):
            if expiry < now:
                del seen[key]
        if command.command_id in seen:
            return CommandResult(command.command_id, ResultCode.DENIED, "Replay detected")
        seen[command.command_id] = float(command.expires_at)
        return CommandResult(command.command_id, ResultCode.OK, "Authorized for adapter dispatch")
