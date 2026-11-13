"""Authenticated command dispatch orchestration (offline library, no network API).

The caller MUST establish device identity through an authenticated transport.
Never accept the token or owner-approval flag from an untrusted intermediary.
"""
from __future__ import annotations

from adapters import DeviceAdapter
from audit_store import AuditStore
from command_protocol import Command, CommandResult, ResultCode
from device_registry import DeviceRegistry
from pairing_store import PairingStore
from replay_store import ReplayStore
from scope_policy import required_scope
from device_consent import ConsentManager
from session_tokens import SessionManager


class SecureDispatcher:
    def __init__(self, pairing: PairingStore, registry: DeviceRegistry,
                 replay: ReplayStore, audit: AuditStore,
                 sessions: SessionManager | None = None,
                 consent: ConsentManager | None = None):
        self.pairing = pairing
        self.registry = registry
        self.replay = replay
        self.audit = audit
        self.adapters: dict[str, DeviceAdapter] = {}
        self.sessions = sessions or SessionManager()
        self.consent = consent or ConsentManager()

    def attach(self, device_id: str, adapter: DeviceAdapter) -> None:
        if self.registry.get(device_id) is None:
            raise ValueError("Device must be registered before adapter attachment")
        self.adapters[device_id] = adapter

    def dispatch(self, command: Command, *, device_token: str,
                 session_id: str = "", session_bearer: str = "",
                 consent_id: str = "") -> CommandResult:
        command.validate()
        device_id = command.device_id
        def deny(code: ResultCode, message: str) -> CommandResult:
            # If audit storage is broken, never proceed to execution.
            self.audit.append("command.denied", device_id)
            return CommandResult(command.command_id, code, message)

        try:
            scope = required_scope(command.action)
            if not self.pairing.authenticate(device_id, device_token, scope):
                return deny(ResultCode.DENIED, "Authentication or scope denied")
            if not self.sessions.verify(session_id, session_bearer, device_id, scope):
                return deny(ResultCode.DENIED, "Session missing or expired")
            device = self.registry.get(device_id)
            if device is None or not device.paired or device.revoked:
                return deny(ResultCode.DENIED, "Device not authorized")
            if command.is_expired():
                return deny(ResultCode.EXPIRED, "Command expired")
            import time
            if not device.online or time.time() - device.last_seen > 90:
                return deny(ResultCode.OFFLINE, "Device offline")
            if command.action not in device.capabilities:
                return deny(ResultCode.UNSUPPORTED, "Capability not verified")
            adapter = self.adapters.get(device_id)
            if adapter is None or command.action not in adapter.supported_actions:
                return deny(ResultCode.UNSUPPORTED, "No approved adapter")
            if not self.replay.reserve(device_id, command.command_id, command.expires_at):
                return deny(ResultCode.DENIED, "Command replayed or expired")
            # Read-only status may proceed without an interactive prompt.
            # Every state-changing action requires a separate trusted local approval.
            if command.action != "status.read" and not self.consent.consume(
                consent_id, device_id, command.command_id, command.action
            ):
                return deny(ResultCode.DENIED, "Local consent required")
            self.audit.append("command.allowed", device_id)
            try:
                result = adapter.execute(command)
                if not isinstance(result, CommandResult) or result.command_id != command.command_id:
                    return CommandResult(command.command_id, ResultCode.FAILED, "Adapter contract violation")
                return result
            except Exception:
                return CommandResult(command.command_id, ResultCode.FAILED, "Adapter failed")
        except (OSError, ValueError, TypeError):
            # Storage/validation failures must not authorize an action.
            return CommandResult(command.command_id, ResultCode.FAILED, "Security subsystem unavailable")
