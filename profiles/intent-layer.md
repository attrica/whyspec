# Intent-layer profile

This optional profile specifies the three objects an implementation exchanges with a harness while
an agent works: the **intention record** it declares before building, the **attestation record**
it writes when it stops, and the **recall line** that records each time governing decisions were
put in front of it. They are the objects §5 and §7 of the governing propagation contract require,
and any harness that wants an implementation to push decisions at the right moment, close the loop
at the end, or be audited on what an agent was shown has to read or write them.

The profile fixes **shapes**: field names, value sets and the rules that make a value honest. It
does not fix how an implementation selects what to push, how many records it pushes, how it derives
a scope from what a session read, what bound it applies to text, how a check decides, or where any
of this is stored — those are implementation judgment and stay outside the specification (§1.4).

An implementation that only reads or writes records need not implement this profile, and
conformance to it is claimed separately from conformance to the core.

**[INT-001]** Each object **MUST** be a single JSON object. An implementation **MAY** keep them as
one object per line in an append-only log; storage is otherwise unspecified. A field this profile
names as optional **MUST** be omitted when it does not apply, never written as `null`, except where
a rule below says a `null` is the honest value.

## The intention record

**[INT-002]** An intention record **MUST** carry: `declared_at` (an ISO-8601 timestamp), `tree_sha`
(the commit the declaration was resolved against, or `null` outside version control), `scope` (a
non-empty array of scope items in the grammar of §4.15), `goal` and `approach` (strings, or `null`
where not yet supplied — see [INT-004]), `matched` (an object mapping each scope item to the count
of artifacts it resolved to), `matched_total` (an integer), `session` (the harness's session
identifier, or `null`), and `origin`.

**[INT-003]** `origin` **MUST** be present and **MUST** be exactly `agent` — the writer declared the
scope — or `harness-reads` — the harness derived the scope from what the session had read before
its first edit. The set is closed. A harness-derived scope that would cover more than an
implementation-defined share of the repository **MUST** be capped to the edited file's directory.
A record whose `origin` is `harness-reads` **MUST** carry `scope_capped`, a boolean that is `true`
when the cap was applied; a record whose `origin` is `agent` **MUST NOT** carry it.

> The two origins are kept apart because they mean different things about the writer. A declared
> scope is a claim the agent made and can be held to; a derived one is an observation the harness
> made about the agent and the agent only confirmed the goal. Reading them the same way would let an
> observation be presented as a commitment. The cap exists because a session that reads widely
> before editing would otherwise record a scope that is most of the repository, and a scope that
> governs everything governs nothing; the share at which that happens is a judgment and is not
> fixed here.

**[INT-004]** `scope` **MUST** be resolved when the record is written, and `matched` **MUST** record
the result, so that a scope resolving to nothing is visible in the record itself rather than
discovered later ([REC-086]). On a record whose `origin` is `harness-reads`, `goal` and `approach`
**MAY** be `null` until the writer supplies them, and a writer **SHOULD** be asked for the goal
before it continues.

**[INT-005]** A binding status or binding version on an intention — whether its scope has been
checked against others, and which versions of the governing records it was resolved against — is
**layer-owned**: it is set by the implementation that stores the record, never by the writer. A
writer **MUST NOT** supply such a field, and a store **MUST NOT** accept one from a writer.

> This is the poisoned-binding defence stated as a shape rule. A writer that could assert its own
> scope as already checked, or name the record versions it claims to have honoured, would be
> granting itself authority the layer exists to withhold.

## The attestation record

**[INT-006]** An attestation record **MUST** carry: `attested_at` (an ISO-8601 timestamp),
`tree_sha` (the commit the session's work stands at), `edited_files` (an array of repository-
relative paths the session changed), `intention` (the intention record it answers, or `null` where
none was recorded), `conformed` (an array of `{record, blob}`), `superseded` (an array of
`{record, blob, why, state}`), `none` (an array of scope items for edited files no record governs),
and `session`.

**[INT-007]** Every entry in `superseded` **MUST** carry `state` equal to `proposed` when the
record is written. A supersession enters only as a proposal: the superseded record keeps binding
until a check passes, and the transition out of `proposed` is made by the layer, never by the
writer. A store **MUST** refuse an attestation whose `superseded` entries carry any other state.

> This is §7's denial of authority, and it needs no exception to the core: currency is derived only
> from `supersedes` relations between records ([REC-111]–[REC-114]), so an attestation moves no
> currency by itself, whatever it says. What the rule adds is that the claim cannot even be
> *written* as more than a proposal.

**[INT-008]** In `conformed` and `superseded`, `record` **MUST** be the repository-relative path of
a record that exists in the tree, and `blob` **MUST** be the content hash of that record as it
stood when attested, so a later reader can tell which version of a decision the writer claims to
have followed or departed from. `why` in a `superseded` entry **MUST** be a non-empty sentence.

**[INT-009]** The attestation record and the `attested` provenance tier ([PROV-001]) are unrelated.
The tier names human rationale written as an aside; the record names a session's account of what
it followed. Neither implies the other.

## The recall line

**[INT-010]** A recall line **MUST** carry: `at` (an ISO-8601 timestamp), `session`, `tool_use_id`
(the harness's identifier for the tool call the push accompanied, or `null`), `path` (the
repository-relative path resolved), `records` (an array of the record paths delivered), `push_outcome`,
`tree_sha` (the commit the resolution ran against), `injected_chars` (an integer count of the text
delivered), and `coupling`. It **MUST** carry `reason` when and only when `push_outcome` is
`resolution_failed`.

**[INT-011]** `push_outcome` **MUST** be exactly `pushed` — at least one record was delivered —
`none_governs` — resolution succeeded and no record governs the path — or `resolution_failed` —
the implementation could not resolve, for the reason given. A resolution made for an edit (`coupling`
`edit`) **MUST** produce a line whatever its outcome, including the two that deliver nothing: a
reader joining this log to a transcript cannot otherwise tell a push that was ignored from one that
never fired. A resolution made at the recorded intention (`coupling` `intention`) **MUST** produce
one line per record delivered for each file in the scope, and produces none when nothing is
delivered.

**[INT-012]** `coupling` **MUST** be present and **MUST** be exactly `edit` — the push made when a
path was first about to be edited — `intention` — the push made at the recorded intention, before
building began — or `spawn`, which is **reserved**: the value is defined so that a reader can
recognise it, and no behaviour is specified for it in this version.

## Implementation note — where a mechanism's configuration lives

*Non-normative.* Every object in this profile is written by a mechanism the harness runs around the
agent — a hook before an edit, a gate at the plan, a guard at stop. A mechanism whose configuration
the governed session can rewrite is voluntary, not enforced: a session asked to attest can instead
delete the hook that asks. Implementations should keep such configuration outside the session's
writable tree, read-only to it, and should detect tampering — for instance by re-hashing the
configuration after the session and by checking that no in-tree configuration was created.
