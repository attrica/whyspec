# Result-envelope transport profile

This optional profile governs metadata attached by a transport after a core command
envelope has been produced. Conformance requires validating the core projection against
`schema/envelope.schema.json` and the complete transported object against
`schema/transport-envelope.schema.json`.

**[ENV-040]** `graph_identity` — or any equivalent block identifying *which corpus answered* —
**MUST NOT** be treated as a core envelope field. It is a **transport-layer credential block**.

The command-line surface carries no transport credential. A transport may attach one after the
core result has been produced without changing the command's result shape.

**[ENV-041]** A transport that attaches a credential block **MUST** attach it unconditionally, with
an explicit `null` when nothing resolved. A key that is sometimes absent is unusable as a
fail-closed signal, because the consumer cannot distinguish "nothing resolved" from "this transport
does not attach it".

**[ENV-042]** A transport-attached key **MUST NOT** collide with any key the core specification
assigns to a command variant.

**[ENV-043]** Transport attachments are **NOT** governed by the core specification's version
marker. Adding, removing, or changing a credential block is a transport event, not a format event,
and **MUST NOT** trigger a core format version bump. Conversely, a consumer **MUST NOT** rely on a
transport attachment as evidence of any core format version.
