"""Trusted in-process owner/device coordination; not a network API.

Only a host application that has independently verified owner identity and
physical UI consent may invoke owner methods. No remote-provided approval flags.
"""
from __future__ import annotations
from dataclasses import dataclass
from pairing_store import PairingStore, PairingInvitation, DeviceCredential
from device_registry import DeviceRegistry, Device
from session_tokens import SessionManager, SessionGrant
from device_consent import ConsentManager, ConsentRequest
from secure_dispatch import SecureDispatcher
from audit_store import AuditStore
from scope_policy import required_scope
from command_protocol import Command, CommandResult


@dataclass(frozen=True)
class VerifiedOwner:
    """Capability object minted by trusted host code after owner login + UI approval."""
    _seal: object


class TrustedController:
    def __init__(self, pairing: PairingStore, registry: DeviceRegistry,
                 sessions: SessionManager, consent: ConsentManager,
                 dispatcher: SecureDispatcher, audit: AuditStore):
        self.pairing = pairing
        self.registry = registry
        self.sessions = sessions
        self.consent = consent
        self.dispatcher = dispatcher
        self.audit = audit
        self._seal = object()

    def owner_approval(self, *, authenticated_owner: bool, local_ui_confirmed: bool) -> VerifiedOwner:
        """ONLY call with results from trusted host login and local UI.

        Boolean inputs are NOT authentication; never bind this to HTTP input.
        """
        if authenticated_owner is not True or local_ui_confirmed is not True:
            raise PermissionError("Owner login and local UI confirmation required")
        return VerifiedOwner(self._seal)

    def _require_owner(self, approval: VerifiedOwner) -> None:
        if not isinstance(approval, VerifiedOwner) or approval._seal is not self._seal:
            raise PermissionError("Trusted owner approval required")

    def invite(self, approval: VerifiedOwner) -> PairingInvitation:
        self._require_owner(approval)
        invitation = self.pairing.begin_pairing(owner_approved=True)
        self.audit.append("pair.created", "owner")
        return invitation

    def pair(self, invitation_id: str, secret: str, device_id: str,
             platform: str, scopes: frozenset[str]) -> DeviceCredential:
        # The caller must independently validate that requested scopes were
        # approved by the owner. Invitation possession alone is not scope approval.
        if not isinstance(platform, str) or not platform or len(platform) > 64:
            raise ValueError("Invalid platform")
        if self.registry.get(device_id) is not None:
            raise ValueError("Device ID already present")
        credential = self.pairing.redeem(invitation_id, secret, device_id, scopes)
        self.registry.register(Device(device_id=device_id, platform=platform))
        self.registry.authorize(device_id)
        self.audit.append("pair.redeemed", device_id)
        return credential

    def start_session(self, device_id: str, token: str, scopes: frozenset[str]) -> SessionGrant:
        from pairing_store import ALLOWED_SCOPES
        if not scopes or not scopes.issubset(ALLOWED_SCOPES):
            raise PermissionError("Invalid scopes")
        if not all(self.pairing.authenticate(device_id, token, scope) for scope in scopes):
            raise PermissionError("Device authentication failed")
        device = self.registry.get(device_id)
        if device is None or not device.paired or device.revoked:
            raise PermissionError("Device is not paired")
        return self.sessions.issue(device_id, scopes, authenticated=True)

    def request_consent(self, command: Command) -> ConsentRequest:
        command.validate()
        return self.consent.request(command.device_id, command.command_id, command.action)

    def approve_consent(self, approval: VerifiedOwner, consent_id: str) -> bool:
        self._require_owner(approval)
        return self.consent.approve(consent_id, trusted_local_ui=True)

    def revoke(self, approval: VerifiedOwner, device_id: str) -> None:
        self._require_owner(approval)
        self.pairing.revoke(device_id, owner_approved=True)
        self.sessions.revoke_device(device_id)
        if self.registry.get(device_id) is not None:
            self.registry.revoke(device_id)
        self.audit.append("device.revoked", device_id)
