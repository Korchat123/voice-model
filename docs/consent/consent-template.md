# Voice data consent record

> Status: **USER INPUT REQUIRED — NOT SIGNED**
>
> This template is a project record, not legal advice. No recording, dataset
> preparation, training, release, or redistribution is authorized until every
> required field is completed and the voice owner and project representative
> have signed the same version.

## Record identity

- Consent ID: `USER_INPUT_REQUIRED`
- Template version: `1.0`
- Effective date (ISO 8601): `USER_INPUT_REQUIRED`
- Voice owner legal name: `USER_INPUT_REQUIRED`
- Preferred/public attribution: `USER_INPUT_REQUIRED`
- Project representative: `USER_INPUT_REQUIRED`
- Related provenance record: `USER_INPUT_REQUIRED`

## Voice owner's authority

The voice owner confirms that:

- [ ] I am the person whose voice will be recorded or I have documented legal
      authority to grant these permissions.
- [ ] I understand that a model may imitate recognizable qualities of my voice.
- [ ] I have received a plain-language explanation of the collection, training,
      evaluation, deployment, and deletion processes.
- [ ] I had an opportunity to ask questions and may refuse without penalty.

## Permission choices

Mark each item **Allow** or **Do not allow**. Blank items mean **not allowed**.

| Activity | Choice | Conditions or limits |
|---|---|---|
| Record new voice samples | `USER_INPUT_REQUIRED` | |
| Process and segment recordings | `USER_INPUT_REQUIRED` | |
| Train or adapt a voice model | `USER_INPUT_REQUIRED` | |
| Run private evaluation | `USER_INPUT_REQUIRED` | |
| Use in the named local AI assistant | `USER_INPUT_REQUIRED` | |
| Generate audio for personal use | `USER_INPUT_REQUIRED` | |
| Generate audio for commercial use | `USER_INPUT_REQUIRED` | |
| Share model weights | `USER_INPUT_REQUIRED` | |
| Share generated audio | `USER_INPUT_REQUIRED` | |
| Share de-identified dataset metadata | `USER_INPUT_REQUIRED` | |
| Share raw or processed recordings | `USER_INPUT_REQUIRED` | |

Named applications, users, organizations, and territories:
`USER_INPUT_REQUIRED`

Explicitly prohibited uses (include impersonation, fraud, harassment, deceptive
political content, and undisclosed endorsement unless counsel approves a
different list):

`USER_INPUT_REQUIRED`

## Retention, disclosure, and revocation

- Raw-recording retention period: `USER_INPUT_REQUIRED`
- Derived-audio retention period: `USER_INPUT_REQUIRED`
- Model/artifact retention period: `USER_INPUT_REQUIRED`
- Approved storage locations and access roles: `USER_INPUT_REQUIRED`
- Generated-audio disclosure requirement: `USER_INPUT_REQUIRED`
- Watermarking requirement: `USER_INPUT_REQUIRED`
- Revocation contact and identity-verification process: `USER_INPUT_REQUIRED`

The voice owner understands that revocation stops future authorized use after
verification and the documented processing period. Copies already lawfully
distributed or incorporated into third-party outputs may not be fully
recoverable; any such limits must be explained here:

`USER_INPUT_REQUIRED`

See [revocation-process.md](revocation-process.md) for the operational procedure.

## Signatures

Signing confirms only the choices explicitly marked above.

- Voice owner signature: `USER_INPUT_REQUIRED`
- Voice owner printed name: `USER_INPUT_REQUIRED`
- Date and timezone: `USER_INPUT_REQUIRED`
- Project representative signature: `USER_INPUT_REQUIRED`
- Project representative printed name: `USER_INPUT_REQUIRED`
- Date and timezone: `USER_INPUT_REQUIRED`
- Guardian/authorized representative, if applicable: `NOT_APPLICABLE_OR_USER_INPUT_REQUIRED`
- Independent witness or legal review, if required: `NOT_APPLICABLE_OR_USER_INPUT_REQUIRED`

## Acceptance gate

This record is valid for project use only when:

- no `USER_INPUT_REQUIRED` value remains;
- every permission has an explicit choice;
- provenance identifiers resolve to immutable, hashed records;
- signatures and dates are present;
- the permitted-use scope matches release and deployment configuration; and
- the signed record is stored outside the public repository with restricted
  access. Only its non-sensitive ID and approval status belong in manifests.
