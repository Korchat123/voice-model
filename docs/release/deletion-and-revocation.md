# Deletion and consent revocation

1. Verify requester authority using the restricted governance process.
2. Immediately disable new synthesis, training, packaging, and distribution for
   the affected consent ID and deny-list affected model checksums.
3. Trace provenance through recordings, derived data, manifests, runs,
   checkpoints, exports, release archives, deployments, caches, backups, and
   distribution records.
4. Delete or retain each item according to signed terms and applicable law;
   record evidence hashes without copying private contents into Git.
5. Rebuild shared artifacts when required, assign new versions/checksums, and
   confirm services reject revoked versions.
6. Notify authorized downstream custodians and document unavoidable recovery
   limits.
7. Verify clean start without the revoked artifact and obtain closure approval.

Never put identity evidence, signatures, private paths, recordings, credentials,
or deletion logs containing personal data into this repository.
