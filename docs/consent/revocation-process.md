# Voice consent revocation process

> Status: **DRAFT — OWNER, CONTACT, AND SERVICE LEVEL REQUIRE USER APPROVAL**

## Purpose

This process stops future use of voice data and derived artifacts when valid
consent is withdrawn. It does not claim that already distributed copies can
always be recovered.

## User-input gate

Before data collection, approve and record:

- revocation contact and an accessible request channel;
- a privacy-preserving identity-verification method;
- acknowledgment and completion time targets;
- which artifacts can be recalled and which cannot;
- legal or contractual retention exceptions; and
- the person authorized to close a revocation request.

## Procedure

1. Register the request with a non-sensitive case ID and timestamp.
2. Verify requester authority without copying identity evidence into Git.
3. Set the consent record to `revocation_pending`; immediately pause new data
   ingestion, training, evaluation, synthesis, packaging, and distribution for
   the affected consent ID.
4. Trace the consent ID through source, processed, dataset, run, checkpoint,
   model, release, backup, and distribution manifests.
5. Quarantine affected releasable artifacts and notify approved downstream
   custodians using the distribution log.
6. Delete or retain each artifact according to the signed terms and applicable
   obligations. Record the action, timestamp, operator, and evidence hash.
7. Rebuild shared datasets or models when removal is technically required and
   feasible. Give rebuilt artifacts new versions and revoke old checksums.
8. Verify that active services cannot load revoked versions.
9. Provide the requester a completion summary, including documented limits.
10. Have an authorized reviewer close the case.

## Evidence checklist

- [ ] Request and authority verified.
- [ ] Consent state changed and processing paused.
- [ ] Lineage and distribution search completed.
- [ ] Storage, backups, caches, packages, and deployments addressed.
- [ ] Downstream custodians notified where applicable.
- [ ] Revoked checksums deny-listed.
- [ ] Replacement versions tested.
- [ ] Completion summary reviewed and delivered.

Do not place signatures, identity documents, private contact information, raw
recordings, or deletion credentials in this repository.
