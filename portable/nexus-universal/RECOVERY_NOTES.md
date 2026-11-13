# Persistent device metadata and crash reconciliation

`device_metadata.py` stores a device's platform in the same SQLite database
as pairing credentials. `reconciliation.py` identifies incomplete records
and restores only known, non-revoked devices that have trusted platform metadata.

Restored devices remain offline with **no capabilities**. Missing metadata is
reported for owner remediation, not silently guessed. Active sessions for
unmapped devices are revoked.

Remaining release blockers:
- Combine credential issuance and platform metadata creation in one trusted
  database transaction; current separate calls have a crash window.
- Restore after verifying the database's ownership, integrity and access
  permissions; a platform string is not proof of platform identity.
- Invalidate all existing sessions when a device is revoked or a pairing is
  rotated; connect this to the final network transport.
- Final automated tests, migration testing and real-device verification.

This code does not grant device permissions or start background services.
