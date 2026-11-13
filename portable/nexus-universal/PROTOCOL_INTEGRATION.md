# NEXUS universal client protocol v1

`client_contract.py` defines a shared strict JSON envelope for Windows,
Linux, macOS and future Android implementations.

Fields: `version` (integer 1), `kind` (allowlisted string),
`request_id` (bounded identifier), `payload` (JSON object).
Maximum serialized size is 8192 bytes. Duplicate JSON keys and non-finite
numbers are rejected. This file deliberately does not send or receive traffic.

`hello` / `hello_ack` negotiate a connection, `heartbeat` is liveness,
`command_result` is a result notification, and `error` reports a bounded
protocol failure. A future transport must define exact payload schemas for
each kind, authenticate each device, bind sessions to credentials and
reject unexpected messages. **Do not treat a hello as authentication.**

Real device commands continue to use `command_protocol.py` with
`secure_dispatch.py`; no arbitrary OS command or USB autorun exists.
This protocol is not yet connected to the Android client or gateway.
