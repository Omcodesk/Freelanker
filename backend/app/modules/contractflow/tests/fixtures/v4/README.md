# V4 synthetic test fixtures

All parties, project/assessment/agreement/reviewer references and review records
are fictional. These files are not production data, actual approvals, signatures
or effective amendments. The synthetic decision authorizes only test drafting.

- `ordering.json`: reference metadata; test support attaches the existing website
  project and V3 ordering-request/assessment examples without altering those files.
- `review_record.json`: a pre-recorded synthetic review attesting the canonical
  agreement/assessment content hashes and versions. It is loaded only by the
  test-support verifier, not created from arbitrary submitted input at verification.
- `provider_output.json`: deterministic fake-provider proposed wording and exact
  field-local citations; not a live Groq output.

Changes to these inputs may invalidate the pinned explicit live demo. Never repin
production records or inject the test verifier into a real review workflow.

## Legacy presentation fixture

`legacy_render.txt` is deterministic synthetic bakery output captured before the
professional presentation change, with a fixed fictional draft UUID. It checks
byte-identical legacy rendering and immutable V5/V6 digest compatibility. It is
not a retained live Groq response, real agreement, approval or legal instrument.
