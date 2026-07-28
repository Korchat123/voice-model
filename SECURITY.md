# Security policy

## Supported versions

Until the first stable release, only the latest commit on the default branch is
supported.

## Reporting

Do not open a public issue for a vulnerability, leaked secret, private
recording, consent violation, or unsafe model artifact. Use GitHub's private
security-advisory reporting for this repository. If that feature is unavailable,
contact the repository owner privately and share only the minimum reproduction.

Include the affected revision, impact, reproduction, and suggested mitigation.
Do not attach real secrets, private speech, or personal data.

## Security boundaries

The service must bind to loopback by default, reject filesystem paths, bound
text and output size, promptly cancel work, and omit full synthesis text from
default logs. Credentials never belong in voice-service requests or repository
configuration.

