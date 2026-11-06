# Synthetic V5 test data

`actors.json` maps fictional opaque demo contexts to roles. Only the test-support
resolver consumes it, and derives IDs from the synthetic bakery project. These
strings are not credentials, signatures or a production identity mechanism.
The amendment is assembled offline from the existing V4 synthetic fixture and
validated before use. No Groq, PayPal or other network request is needed.
