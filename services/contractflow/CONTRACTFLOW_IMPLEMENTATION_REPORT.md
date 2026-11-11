# ContractFlow Implementation and Integration Report

**Audit date:** 10 November 2026, Asia/Calcutta. **Owner:** Person 2, ContractFlow
backend. Evidence: inspected source, fresh offline execution and read-only remote
branch inspection. Synthetic verification is not production integration or legal
execution. All local paths below are relative to this module unless stated otherwise.

## 1. Executive summary

V1–V5 domain workflows and V6's exported HTTP layer work in the verified offline
environment. The full suite executed for this audit returned **902 passed,
0 failed, 0 skipped, 1 warning in 32.49s**. **107 Python files** parsed successfully.
The API examples below were executed separately in an in-process ASGI app with
test-only providers/adapters, then validated against the actual Pydantic schemas.

**Production integration remains incomplete.** The inspected Core Platform branch
contains only LICENSE. ContractFlow has no operational PostgreSQL repository,
session factory, migration or real auth/review adapter. A WorkBridge implementation
now exists on a separate remote branch, but is not merged here and has significant
identity, data-shape, lifecycle and transaction differences. Its approval hook must
not be connected automatically to V5 approval state or payment execution.

Deterministic validation does not establish semantic correctness, legal completeness,
signature or enforceability. Human and semantic review remain required. The V4
artifact retains effective=false and parties_approved=false; BOTH_APPROVED is a
separate V5 workflow state and does not change the original agreement.

## 2. Actual Git and repository state

| Item | Verified value |
|---|---|
| Repository | https://github.com/Omcodesk/Freelanker |
| Current branch | feature/contractflow |
| Actual HEAD | `0608adf2fce1f10d42c62141f38f1a4348e4e7ca` |
| HEAD subject | docs(contractflow): add integration and setup documentation |
| Previous rendering implementation | `cd3a5d9b933e3a7e13586a1247825a79877e2556` |
| Tracking | origin/feature/contractflow; 0 ahead, 0 behind |
| Actual remote tip from git ls-remote | Same full hash as HEAD; committed baseline is pushed |
| Tracked modifications at audit start | None |
| Existing untracked content | .venv/, module __pycache__/ directories, output/ PDF; untouched |
| This task | Only this report is added; not staged, committed or pushed |

The previous rendering hash is not the latest HEAD. `git diff cd3a5d9 HEAD
--name-only` showed only README.md; application implementation is unchanged by the
later documentation commit. Remote heads were checked with `git ls-remote --heads
origin`; the new Core/WorkBridge refs were fetched for inspection, without checkout
or merge. This updates Git metadata, not source files.

| Remote branch | Inspected tip | Available architecture |
|---|---|---|
| feature/contractflow | `0608adf2fce1f10d42c62141f38f1a4348e4e7ca` | ContractFlow code and documentation |
| feature/core-platform | `a87339908a55da4435d2368d8bc9b25ea83491e3` | LICENSE only; no shared app/auth/DB |
| main | `a87339908a55da4435d2368d8bc9b25ea83491e3` | LICENSE only |
| workbridge | `d5e7af5f1038f5da782f4377cf1dfc446baedee8` | Standalone FastAPI, sync SQLAlchemy/SQLite, React frontend |

No claim covers external repositories or unpushed teammate work. README and
V6_HANDOFF contain earlier verification snapshots; this report records the fresh audit.

## 3. Implementation status matrix

**COMPLETED** means implemented and verified in the stated environment.
**PARTIALLY COMPLETED** means implementation exists but essential integration remains.
**PENDING** means not implemented for ContractFlow production use.

| Feature | Status | Implemented functionality | Evidence | Remaining work |
|---|---|---|---|---|
| V1 AI Contract Generation | COMPLETED | Async extractive contract sections; immutable facts; fake-provider verification | service.py, schemas.py, tests/test_service.py | Production source/provider configuration |
| V2 AI Agreement Drafting | COMPLETED | Controlled paraphrases, source references, deterministic assembly, review flags | v2/service.py, v2/validation.py, tests/test_v2_service.py | Human semantic review and production adapters |
| V3 Scope Change Detection | COMPLETED | Three classifications, field-local evidence, quantitative guards, deterministic actions | v3/service.py, v3/validation.py, tests/test_v3_service.py | Real authoritative source/review integration |
| V4 Amendment Generation | COMPLETED | Inactive proposals, trusted assessment review boundary, professional/legacy rendering | v4/service.py, v4/renderer.py, tests/test_v4_professional_rendering.py | Real review store and semantic quality review |
| V5 Dual-Party Approval | COMPLETED | Same revision/digest, distinct parties, idempotency, terminal rejection, supersession, atomic memory audit/state | v5/service.py, v5/repository.py, tests/test_v5_workflow.py | Completed standalone scope only; durable production adapters still needed |
| V6 FastAPI endpoints | PARTIALLY COMPLETED | Eight handlers, strict schemas, body limit, safe errors and fake-adapter HTTP flow | api/router.py, tests/test_v6_api.py, tests/test_v6_integration.py | Shared app mounting and real runtime dependencies |
| Real authentication/authorization | PARTIALLY COMPLETED | Required trust interfaces and exact party/project checks | api/dependencies.py, integrations/contracts.py, v5/authorization.py | Actual sessions/tokens, membership, permissions and revocation |
| Real WorkBridge integration | PARTIALLY COMPLETED | Source protocol, immutable snapshot validation and freshness checks | integrations/contracts.py, integrations/workflow.py | Map complete upstream facts and connect real adapter |
| PostgreSQL persistence | PARTIALLY COMPLETED | Artifact/repository/UoW interfaces and schema proposal | persistence/artifacts.py, persistence/POSTGRESQL_DESIGN.md | Models, sessions, durable repositories and PostgreSQL tests |
| Database migrations | PENDING | Requirements documented only | persistence/POSTGRESQL_DESIGN.md | Approved Alembic environment and CF migrations |
| Shared application mounting | PENDING | Router export and instructions | api/router.py, V6_HANDOFF.md | Core-owned app factory and include_router once |
| Real client/freelancer data | PENDING | Strict ProjectInput and SourceSnapshot | schemas.py, integrations/contracts.py | Authenticated IDs and complete authoritative versioned facts |
| Frontend integration | PENDING | API contracts | api/schemas.py | Teammate consumes authenticated CF endpoints |
| Production approval transactions | PARTIALLY COMPLETED | Transaction protocol, single-process atomic memory repository/test UoW | integrations/contracts.py, v5/repository.py, tests/v6_support.py | DB uniqueness/locks, revocation serialization, multi-session tests |
| Payment execution/amendment activation | PENDING | Intentionally absent; approval is not execution | v4/schemas.py, v5/schemas.py, v4/renderer.py | Separately authorized future workflow, not an automatic merge step |

## 4. Folder structure and responsibilities

```text
contractflow/
  service.py, schemas.py, prompts.py, errors.py   V1 service/facts/errors
  config.py                                    Explicit Groq settings
  providers/base.py, providers/groq.py          Provider protocol/SDK adapter
  v2/                                          Agreement drafting/assembly
  v3/                                          Scope/evidence/quantity validation
  v4/                                          Amendment/review/rendering/quality
  v5/                                          Approval/identity/state/repository/audit
  api/router.py, api/schemas.py                 Eight routes and HTTP bodies
  api/dependencies.py, api/errors.py            Fail-closed DI and safe responses
  integrations/contracts.py                    Auth/source/review/transaction ports
  integrations/workflow.py                     IntegrationRuntime orchestration
  persistence/artifacts.py                     ArtifactRepository/StoredArtifact
  persistence/POSTGRESQL_DESIGN.md              Proposed, non-operational DB design
  tests/ and tests/fixtures/                    Offline tests and synthetic data
  tests/v4_support.py, v5_support.py, v6_support.py  Test-only trusted/fake adapters
  demo_v5.py                                   Offline approval/revision/rejection demo
  live_test.py, live_test_v2.py, live_test_v3.py, live_test_v4.py  Optional live runners
  README.md, V6_HANDOFF.md                      Setup/integration documentation
  CONTRACTFLOW_IMPLEMENTATION_REPORT.md         This audit
```

Public async domain methods: V1/V2 `generate_contract(project_data)`, V3
`assess_scope_change(input_data)`, V4 `generate_amendment(request)`, V5
`register_amendment`, `submit_decision`, `get_status`, `get_history`. These services
do not depend on a shared FastAPI application; V6 supplies HTTP orchestration.

## 5. API implementation and exact examples

### 5.1 Mounting, authority and schemas

Prefix: `/api/v1/contractflow`. **Exported handlers are implemented, but the router
is not mounted in a shared application and production URLs are not operational.**
The executing app in this audit is the in-process test app from tests/v6_support.py,
configured only with synthetic dependencies. Missing credentials return 401; a
credential with no configured runtime returns 503. There is no production fallback.

| Method | Full path | Request schema | Response schema | Authentication/authorization |
|---|---|---|---|---|
| POST | /api/v1/contractflow/contracts/generate | ProjectRequest | StoredArtifact CONTRACT | Bearer; own project; write permission |
| POST | /api/v1/contractflow/agreements/draft | ProjectRequest | StoredArtifact AGREEMENT | Bearer; own project; write permission |
| POST | /api/v1/contractflow/scope/assess | AssessmentRequest | StoredArtifact ASSESSMENT | Bearer; write permission; original agreement |
| POST | /api/v1/contractflow/amendments/generate | AmendmentRequest | StoredArtifact AMENDMENT | Bearer; write permission; stored OUT_OF_SCOPE assessment and trusted assessment review |
| POST | /api/v1/contractflow/amendments/{amendment_id}/register | RegisterRequest | ApprovalStatus | Bearer; own party; write permission; current trusted reviews |
| POST | /api/v1/contractflow/amendments/{amendment_id}/decisions | DecisionBody | ApprovalStatus | Bearer; own party; exact revision/digest; current trusted reviews |
| GET | /api/v1/contractflow/amendments/{amendment_id}/status | No body | ApprovalStatus | Bearer; own party; read permission; current trusted reviews |
| GET | /api/v1/contractflow/amendments/{amendment_id}/history | No body | tuple[AuditEvent, ...], JSON array | Bearer; own party; read permission; current trusted reviews |

ProjectRequest: project_id + expected_source_version. AssessmentRequest adds
client_request and optional supporting_context ({id,text} array). AmendmentRequest
adds assessment_id UUID and review_reference. RegisterRequest has expected_version
and expected_digest. DecisionBody adds APPROVE/REJECT, idempotency_key and optional
rejection_reason only for REJECT. Amendment path IDs are UUIDs.

Body limit: 131072 streamed bytes. API IDs: strict strings of 1–128 characters;
versions: strict positive integers; digests: 64 lowercase hex characters; client
request: 1–8000 characters; supporting context: at most 10 entries; rejection reason:
1–1000 characters, no control characters. Existing domain safety limits also apply.
Caller-supplied roles, approval/review flags or authoritative facts are forbidden.

StoredArtifact includes server identity/version/time, kind, source, content_digest
and payload_json: a JSON STRING containing the complete validated domain artifact,
not raw LLM output. Registration expects the **archive digest**. Decisions expect
the **V5 approval digest** returned by register/status; the two are not interchangeable.

Errors use `{"error":{"code":"FIXED_CODE"}}`, suppressing raw exceptions/inputs:
401 UNAUTHENTICATED; 403 FORBIDDEN/REVIEW_INVALID; 404 NOT_FOUND;
409 STALE_SOURCE/MISSING_AGREEMENT/WORKFLOW_CONFLICT; 413 REQUEST_TOO_LARGE;
422 INVALID_REQUEST; 502 PROVIDER_FAILED; 503 UNAVAILABLE/INTEGRATION_UNAVAILABLE/
PROVIDER_TIMEOUT. Missing auth includes WWW-Authenticate. No custom400 behavior is
invented: router schema errors are 422. See api/errors.py for actual mappings.

### 5.2 Sample provenance

All eight examples below are actual in-process HTTP calls made during this audit
with test-only synthetic adapters. Every request and response is validated against
the current route's Pydantic model. All parties/projects/reviews are fictional;
UUIDs/timestamps are server-generated in that run, not real account credentials,
legal approvals or production records. Responses are complete, including escaped
payload_json, inside collapsible blocks; no required fields are omitted.

The decision example records CLIENT's first approval. An additional successful
FREELANCER decision with a different key precedes GET status/history, so their
BOTH_APPROVED state and three events (CREATED plus two decisions) belong to the
same amendment/digest. GET requests have no JSON body. No real bearer token is shown.

### 5.3 `POST /api/v1/contractflow/contracts/generate`

Extractive contract from the authorized project snapshot. Errors:401/404 access,409 stale source,422 schema,502 provider,503 integration/storage.

Synthetic JSON request:

```json
{
  "project_id": "SYNTHETIC-WEB-001",
  "expected_source_version": 1
}
```

<details>
<summary>Complete observed synthetic HTTP 200 JSON response</summary>

```json
{
  "artifact_id": "bbf74daf-2797-49ff-9288-eafc198da4b2",
  "artifact_version": 1,
  "kind": "CONTRACT",
  "source": {
    "source_version": 1,
    "project": {
      "project_id": "SYNTHETIC-WEB-001",
      "title": "Fictional bakery website",
      "client": {
        "id": "TEST-CLIENT-1",
        "name": "Example Bakery (Synthetic)"
      },
      "freelancer": {
        "id": "TEST-FREELANCER-1",
        "name": "Example Developer (Synthetic)"
      },
      "scope": "Build a responsive three-page bakery website using client-supplied copy and images.",
      "budget": "1200.00",
      "currency": "USD",
      "start_date": "2027-01-04",
      "deadline": "2027-01-29",
      "deliverables": [
        {
          "id": "D1",
          "description": "Home, menu and contact page source files.",
          "deadline": "2027-01-22"
        },
        {
          "id": "D2",
          "description": "Website deployment instructions.",
          "deadline": "2027-01-29"
        }
      ],
      "milestones": [
        {
          "id": "M1",
          "description": "Deliver website page source files.",
          "deadline": "2027-01-22",
          "deliverable_ids": [
            "D1"
          ]
        },
        {
          "id": "M2",
          "description": "Deliver deployment documentation.",
          "deadline": "2027-01-29",
          "deliverable_ids": [
            "D2"
          ]
        }
      ]
    },
    "agreement": {
      "agreement_id": "SYNTHETIC-AGREEMENT-1",
      "version": 1,
      "project": {
        "project_id": "SYNTHETIC-WEB-001",
        "title": "Fictional bakery website",
        "client": {
          "id": "TEST-CLIENT-1",
          "name": "Example Bakery (Synthetic)"
        },
        "freelancer": {
          "id": "TEST-FREELANCER-1",
          "name": "Example Developer (Synthetic)"
        },
        "scope": "Build a responsive three-page bakery website using client-supplied copy and images.",
        "budget": "1200.00",
        "currency": "USD",
        "start_date": "2027-01-04",
        "deadline": "2027-01-29",
        "deliverables": [
          {
            "id": "D1",
            "description": "Home, menu and contact page source files.",
            "deadline": "2027-01-22"
          },
          {
            "id": "D2",
            "description": "Website deployment instructions.",
            "deadline": "2027-01-29"
          }
        ],
        "milestones": [
          {
            "id": "M1",
            "description": "Deliver website page source files.",
            "deadline": "2027-01-22",
            "deliverable_ids": [
              "D1"
            ]
          },
          {
            "id": "M2",
            "description": "Deliver deployment documentation.",
            "deadline": "2027-01-29",
            "deliverable_ids": [
              "D2"
            ]
          }
        ]
      }
    }
  },
  "content_digest": "7966e5a24dc6ec4d5e704d0d74ec7b155df88b2f13e1722e47754dc45e26fedb",
  "created_at": "2026-11-10T08:03:07.720390Z",
  "payload_json": "{\"label\":\"DRAFT — REQUIRES CLIENT AND FREELANCER REVIEW\",\"requires_human_review\":true,\"authoritative_data\":{\"project_id\":\"SYNTHETIC-WEB-001\",\"title\":\"Fictional bakery website\",\"client\":{\"id\":\"TEST-CLIENT-1\",\"name\":\"Example Bakery (Synthetic)\"},\"freelancer\":{\"id\":\"TEST-FREELANCER-1\",\"name\":\"Example Developer (Synthetic)\"},\"scope\":\"Build a responsive three-page bakery website using client-supplied copy and images.\",\"budget\":\"1200.00\",\"currency\":\"USD\",\"start_date\":\"2027-01-04\",\"deadline\":\"2027-01-29\",\"deliverables\":[{\"id\":\"D1\",\"description\":\"Home, menu and contact page source files.\",\"deadline\":\"2027-01-22\"},{\"id\":\"D2\",\"description\":\"Website deployment instructions.\",\"deadline\":\"2027-01-29\"}],\"milestones\":[{\"id\":\"M1\",\"description\":\"Deliver website page source files.\",\"deadline\":\"2027-01-22\",\"deliverable_ids\":[\"D1\"]},{\"id\":\"M2\",\"description\":\"Deliver deployment documentation.\",\"deadline\":\"2027-01-29\",\"deliverable_ids\":[\"D2\"]}]},\"ai_wording\":{\"sections\":[{\"source_ref\":\"scope\",\"text\":\"Build a responsive three-page bakery website using client-supplied copy and images.\"},{\"source_ref\":\"deliverables/0\",\"text\":\"Home, menu and contact page source files.\"},{\"source_ref\":\"deliverables/1\",\"text\":\"Website deployment instructions.\"},{\"source_ref\":\"milestones/0\",\"text\":\"Deliver website page source files.\"},{\"source_ref\":\"milestones/1\",\"text\":\"Deliver deployment documentation.\"}]},\"unresolved_terms\":[\"governing_law\",\"intellectual_property_ownership\",\"termination_conditions\",\"penalties\",\"payment_schedule\",\"acceptance_conditions\",\"other_legal_or_commercial_terms\"]}"
}
```

</details>

### 5.4 `POST /api/v1/contractflow/agreements/draft`

Controlled agreement wording with immutable facts. Errors:401/404,409 stale source,422 schema,502 provider,503 integration/storage.

Synthetic JSON request:

```json
{
  "project_id": "SYNTHETIC-WEB-001",
  "expected_source_version": 1
}
```

<details>
<summary>Complete observed synthetic HTTP 200 JSON response</summary>

```json
{
  "artifact_id": "7fd2f0d4-cffb-4f56-ba05-ffd723dbd2ad",
  "artifact_version": 1,
  "kind": "AGREEMENT",
  "source": {
    "source_version": 1,
    "project": {
      "project_id": "SYNTHETIC-WEB-001",
      "title": "Fictional bakery website",
      "client": {
        "id": "TEST-CLIENT-1",
        "name": "Example Bakery (Synthetic)"
      },
      "freelancer": {
        "id": "TEST-FREELANCER-1",
        "name": "Example Developer (Synthetic)"
      },
      "scope": "Build a responsive three-page bakery website using client-supplied copy and images.",
      "budget": "1200.00",
      "currency": "USD",
      "start_date": "2027-01-04",
      "deadline": "2027-01-29",
      "deliverables": [
        {
          "id": "D1",
          "description": "Home, menu and contact page source files.",
          "deadline": "2027-01-22"
        },
        {
          "id": "D2",
          "description": "Website deployment instructions.",
          "deadline": "2027-01-29"
        }
      ],
      "milestones": [
        {
          "id": "M1",
          "description": "Deliver website page source files.",
          "deadline": "2027-01-22",
          "deliverable_ids": [
            "D1"
          ]
        },
        {
          "id": "M2",
          "description": "Deliver deployment documentation.",
          "deadline": "2027-01-29",
          "deliverable_ids": [
            "D2"
          ]
        }
      ]
    },
    "agreement": {
      "agreement_id": "SYNTHETIC-AGREEMENT-1",
      "version": 1,
      "project": {
        "project_id": "SYNTHETIC-WEB-001",
        "title": "Fictional bakery website",
        "client": {
          "id": "TEST-CLIENT-1",
          "name": "Example Bakery (Synthetic)"
        },
        "freelancer": {
          "id": "TEST-FREELANCER-1",
          "name": "Example Developer (Synthetic)"
        },
        "scope": "Build a responsive three-page bakery website using client-supplied copy and images.",
        "budget": "1200.00",
        "currency": "USD",
        "start_date": "2027-01-04",
        "deadline": "2027-01-29",
        "deliverables": [
          {
            "id": "D1",
            "description": "Home, menu and contact page source files.",
            "deadline": "2027-01-22"
          },
          {
            "id": "D2",
            "description": "Website deployment instructions.",
            "deadline": "2027-01-29"
          }
        ],
        "milestones": [
          {
            "id": "M1",
            "description": "Deliver website page source files.",
            "deadline": "2027-01-22",
            "deliverable_ids": [
              "D1"
            ]
          },
          {
            "id": "M2",
            "description": "Deliver deployment documentation.",
            "deadline": "2027-01-29",
            "deliverable_ids": [
              "D2"
            ]
          }
        ]
      }
    }
  },
  "content_digest": "2ca28166b981ba5190eb6809a457bc9b8dfc2a9fa26793f39d3e42adc816ed28",
  "created_at": "2026-11-10T08:03:07.765183Z",
  "payload_json": "{\"version\":\"2\",\"label\":\"DRAFT — REQUIRES CLIENT AND FREELANCER REVIEW\",\"requires_human_review\":true,\"semantic_review_required\":true,\"deterministic_checks\":\"passed; semantic equivalence not established\",\"authoritative_data\":{\"project_id\":\"SYNTHETIC-WEB-001\",\"title\":\"Fictional bakery website\",\"client\":{\"id\":\"TEST-CLIENT-1\",\"name\":\"Example Bakery (Synthetic)\"},\"freelancer\":{\"id\":\"TEST-FREELANCER-1\",\"name\":\"Example Developer (Synthetic)\"},\"scope\":\"Build a responsive three-page bakery website using client-supplied copy and images.\",\"budget\":\"1200.00\",\"currency\":\"USD\",\"start_date\":\"2027-01-04\",\"deadline\":\"2027-01-29\",\"deliverables\":[{\"id\":\"D1\",\"description\":\"Home, menu and contact page source files.\",\"deadline\":\"2027-01-22\"},{\"id\":\"D2\",\"description\":\"Website deployment instructions.\",\"deadline\":\"2027-01-29\"}],\"milestones\":[{\"id\":\"M1\",\"description\":\"Deliver website page source files.\",\"deadline\":\"2027-01-22\",\"deliverable_ids\":[\"D1\"]},{\"id\":\"M2\",\"description\":\"Deliver deployment documentation.\",\"deadline\":\"2027-01-29\",\"deliverable_ids\":[\"D2\"]}]},\"ai_wording\":{\"sections\":[{\"source_ref\":\"scope\",\"text\":\"Develop a responsive website of three pages for the bakery, using copy and images supplied by the client.\"},{\"source_ref\":\"deliverables/0\",\"text\":\"Provide the source files for the home, menu and contact pages.\"},{\"source_ref\":\"deliverables/1\",\"text\":\"Provide instructions for deploying the website.\"},{\"source_ref\":\"milestones/0\",\"text\":\"Supply the source files for the website pages.\"},{\"source_ref\":\"milestones/1\",\"text\":\"Supply documentation describing website deployment.\"}]},\"sections\":[{\"title\":\"Parties\",\"paragraphs\":[\"Client: Example Bakery (Synthetic) (ID: TEST-CLIENT-1).\",\"Freelancer: Example Developer (Synthetic) (ID: TEST-FREELANCER-1).\",\"Project: Fictional bakery website (ID: SYNTHETIC-WEB-001).\"]},{\"title\":\"Scope of work\",\"paragraphs\":[\"Source [scope]: Build a responsive three-page bakery website using client-supplied copy and images.\",\"Proposed wording: Develop a responsive website of three pages for the bakery, using copy and images supplied by the client.\"]},{\"title\":\"Deliverables\",\"paragraphs\":[\"D1 — Due 2027-01-22. Source [deliverables/0]: Home, menu and contact page source files.\\nProposed wording: Provide the source files for the home, menu and contact pages.\",\"D2 — Due 2027-01-29. Source [deliverables/1]: Website deployment instructions.\\nProposed wording: Provide instructions for deploying the website.\"]},{\"title\":\"Milestones and timeline\",\"paragraphs\":[\"Project start: 2027-01-04; deadline: 2027-01-29.\",\"M1 — Due 2027-01-22; deliverables: D1. Source [milestones/0]: Deliver website page source files.\\nProposed wording: Supply the source files for the website pages.\",\"M2 — Due 2027-01-29; deliverables: D2. Source [milestones/1]: Deliver deployment documentation.\\nProposed wording: Supply documentation describing website deployment.\"]},{\"title\":\"Compensation\",\"paragraphs\":[\"Project budget: 1200.00 USD.\",\"Payment schedule is unresolved; delivery milestones do not establish payment dates.\"]},{\"title\":\"Unresolved terms\",\"paragraphs\":[\"Governing law: unresolved — requires human review.\",\"Intellectual property ownership: unresolved — requires human review.\",\"Termination conditions: unresolved — requires human review.\",\"Penalties: unresolved — requires human review.\",\"Payment schedule: unresolved — requires human review.\",\"Acceptance conditions: unresolved — requires human review.\",\"Other legal or commercial terms: unresolved — requires human review.\"]}],\"unresolved_terms\":[\"governing_law\",\"intellectual_property_ownership\",\"termination_conditions\",\"penalties\",\"payment_schedule\",\"acceptance_conditions\",\"other_legal_or_commercial_terms\"]}"
}
```

</details>

### 5.5 `POST /api/v1/contractflow/scope/assess`

Original agreement required; change text/context are untrusted. Errors:401/404,409 missing agreement or stale source,422 schema,502 provider,503 integration.

Synthetic JSON request:

```json
{
  "project_id": "SYNTHETIC-WEB-001",
  "expected_source_version": 1,
  "client_request": "Add an online ordering system with payment integration.",
  "supporting_context": []
}
```

<details>
<summary>Complete observed synthetic HTTP 200 JSON response</summary>

```json
{
  "artifact_id": "387d0187-adb0-44d7-a275-23647fa86b97",
  "artifact_version": 1,
  "kind": "ASSESSMENT",
  "source": {
    "source_version": 1,
    "project": {
      "project_id": "SYNTHETIC-WEB-001",
      "title": "Fictional bakery website",
      "client": {
        "id": "TEST-CLIENT-1",
        "name": "Example Bakery (Synthetic)"
      },
      "freelancer": {
        "id": "TEST-FREELANCER-1",
        "name": "Example Developer (Synthetic)"
      },
      "scope": "Build a responsive three-page bakery website using client-supplied copy and images.",
      "budget": "1200.00",
      "currency": "USD",
      "start_date": "2027-01-04",
      "deadline": "2027-01-29",
      "deliverables": [
        {
          "id": "D1",
          "description": "Home, menu and contact page source files.",
          "deadline": "2027-01-22"
        },
        {
          "id": "D2",
          "description": "Website deployment instructions.",
          "deadline": "2027-01-29"
        }
      ],
      "milestones": [
        {
          "id": "M1",
          "description": "Deliver website page source files.",
          "deadline": "2027-01-22",
          "deliverable_ids": [
            "D1"
          ]
        },
        {
          "id": "M2",
          "description": "Deliver deployment documentation.",
          "deadline": "2027-01-29",
          "deliverable_ids": [
            "D2"
          ]
        }
      ]
    },
    "agreement": {
      "agreement_id": "SYNTHETIC-AGREEMENT-1",
      "version": 1,
      "project": {
        "project_id": "SYNTHETIC-WEB-001",
        "title": "Fictional bakery website",
        "client": {
          "id": "TEST-CLIENT-1",
          "name": "Example Bakery (Synthetic)"
        },
        "freelancer": {
          "id": "TEST-FREELANCER-1",
          "name": "Example Developer (Synthetic)"
        },
        "scope": "Build a responsive three-page bakery website using client-supplied copy and images.",
        "budget": "1200.00",
        "currency": "USD",
        "start_date": "2027-01-04",
        "deadline": "2027-01-29",
        "deliverables": [
          {
            "id": "D1",
            "description": "Home, menu and contact page source files.",
            "deadline": "2027-01-22"
          },
          {
            "id": "D2",
            "description": "Website deployment instructions.",
            "deadline": "2027-01-29"
          }
        ],
        "milestones": [
          {
            "id": "M1",
            "description": "Deliver website page source files.",
            "deadline": "2027-01-22",
            "deliverable_ids": [
              "D1"
            ]
          },
          {
            "id": "M2",
            "description": "Deliver deployment documentation.",
            "deadline": "2027-01-29",
            "deliverable_ids": [
              "D2"
            ]
          }
        ]
      }
    }
  },
  "content_digest": "dbaa04ec0c840c96d99567267cca468f2226fc6d0e4d0fd4ebb4c296fdc5d284",
  "created_at": "2026-11-10T08:03:07.813617Z",
  "payload_json": "{\"version\":\"3\",\"request_id\":\"f4ba1f4f-b127-424e-af83-59fb6118d767\",\"project_id\":\"SYNTHETIC-WEB-001\",\"input_snapshot\":{\"request_id\":\"f4ba1f4f-b127-424e-af83-59fb6118d767\",\"project_id\":\"SYNTHETIC-WEB-001\",\"original_project\":{\"project_id\":\"SYNTHETIC-WEB-001\",\"title\":\"Fictional bakery website\",\"client\":{\"id\":\"TEST-CLIENT-1\",\"name\":\"Example Bakery (Synthetic)\"},\"freelancer\":{\"id\":\"TEST-FREELANCER-1\",\"name\":\"Example Developer (Synthetic)\"},\"scope\":\"Build a responsive three-page bakery website using client-supplied copy and images.\",\"budget\":\"1200.00\",\"currency\":\"USD\",\"start_date\":\"2027-01-04\",\"deadline\":\"2027-01-29\",\"deliverables\":[{\"id\":\"D1\",\"description\":\"Home, menu and contact page source files.\",\"deadline\":\"2027-01-22\"},{\"id\":\"D2\",\"description\":\"Website deployment instructions.\",\"deadline\":\"2027-01-29\"}],\"milestones\":[{\"id\":\"M1\",\"description\":\"Deliver website page source files.\",\"deadline\":\"2027-01-22\",\"deliverable_ids\":[\"D1\"]},{\"id\":\"M2\",\"description\":\"Deliver deployment documentation.\",\"deadline\":\"2027-01-29\",\"deliverable_ids\":[\"D2\"]}]},\"client_request\":\"Add an online ordering system with payment integration.\",\"supporting_context\":[]},\"analysis\":{\"classification\":\"OUT_OF_SCOPE\",\"explanation\":\"Online ordering and payment integration appear to add functionality beyond the described website and page source deliverables.\",\"source_references\":[{\"reference\":\"original.scope\",\"excerpt\":\"Build a responsive three-page bakery website using client-supplied copy and images.\"},{\"reference\":\"original.deliverables/0/description\",\"excerpt\":\"Home, menu and contact page source files.\"}],\"requested_changes\":[{\"description\":\"Add online ordering with payment integration.\",\"request_evidence\":{\"reference\":\"request.client_request\",\"excerpt\":\"Add an online ordering system with payment integration.\"},\"source_references\":[{\"reference\":\"original.scope\",\"excerpt\":\"Build a responsive three-page bakery website using client-supplied copy and images.\"}]}],\"potential_impacts\":[{\"category\":\"DELIVERABLES\",\"explanation\":\"Additional ordering functionality could expand the agreed deliverables.\",\"source_references\":[{\"reference\":\"original.deliverables/0/description\",\"excerpt\":\"Home, menu and contact page source files.\"}]},{\"category\":\"TIMELINE\",\"explanation\":\"The implementation effort could affect the project timeline; review is needed.\",\"source_references\":[{\"reference\":\"original.deadline\",\"excerpt\":\"2027-01-29\"}]},{\"category\":\"COMPENSATION\",\"explanation\":\"Additional effort could require a compensation discussion, subject to human review.\",\"source_references\":[{\"reference\":\"original.budget\",\"excerpt\":\"1200.00\"}]}],\"clarification_questions\":[],\"context_references\":[]},\"recommended_action\":\"PROPOSE_AMENDMENT\",\"human_review_required\":true,\"semantic_review_required\":true,\"deterministic_validation\":\"passed; semantic correctness not established\"}"
}
```

</details>

### 5.6 `POST /api/v1/contractflow/amendments/generate`

Stored assessment must be reviewed OUT_OF_SCOPE and match the current source. Errors:401,403 trusted review denial,404 assessment,409 source,422 schema,502 provider,503 storage.

Synthetic JSON request:

```json
{
  "project_id": "SYNTHETIC-WEB-001",
  "expected_source_version": 1,
  "assessment_id": "387d0187-adb0-44d7-a275-23647fa86b97",
  "review_reference": "synthetic-review:387d0187-adb0-44d7-a275-23647fa86b97"
}
```

<details>
<summary>Complete observed synthetic HTTP 200 JSON response</summary>

```json
{
  "artifact_id": "c15d4d4f-30ef-4852-97f9-dcaa5587a9c0",
  "artifact_version": 1,
  "kind": "AMENDMENT",
  "source": {
    "source_version": 1,
    "project": {
      "project_id": "SYNTHETIC-WEB-001",
      "title": "Fictional bakery website",
      "client": {
        "id": "TEST-CLIENT-1",
        "name": "Example Bakery (Synthetic)"
      },
      "freelancer": {
        "id": "TEST-FREELANCER-1",
        "name": "Example Developer (Synthetic)"
      },
      "scope": "Build a responsive three-page bakery website using client-supplied copy and images.",
      "budget": "1200.00",
      "currency": "USD",
      "start_date": "2027-01-04",
      "deadline": "2027-01-29",
      "deliverables": [
        {
          "id": "D1",
          "description": "Home, menu and contact page source files.",
          "deadline": "2027-01-22"
        },
        {
          "id": "D2",
          "description": "Website deployment instructions.",
          "deadline": "2027-01-29"
        }
      ],
      "milestones": [
        {
          "id": "M1",
          "description": "Deliver website page source files.",
          "deadline": "2027-01-22",
          "deliverable_ids": [
            "D1"
          ]
        },
        {
          "id": "M2",
          "description": "Deliver deployment documentation.",
          "deadline": "2027-01-29",
          "deliverable_ids": [
            "D2"
          ]
        }
      ]
    },
    "agreement": {
      "agreement_id": "SYNTHETIC-AGREEMENT-1",
      "version": 1,
      "project": {
        "project_id": "SYNTHETIC-WEB-001",
        "title": "Fictional bakery website",
        "client": {
          "id": "TEST-CLIENT-1",
          "name": "Example Bakery (Synthetic)"
        },
        "freelancer": {
          "id": "TEST-FREELANCER-1",
          "name": "Example Developer (Synthetic)"
        },
        "scope": "Build a responsive three-page bakery website using client-supplied copy and images.",
        "budget": "1200.00",
        "currency": "USD",
        "start_date": "2027-01-04",
        "deadline": "2027-01-29",
        "deliverables": [
          {
            "id": "D1",
            "description": "Home, menu and contact page source files.",
            "deadline": "2027-01-22"
          },
          {
            "id": "D2",
            "description": "Website deployment instructions.",
            "deadline": "2027-01-29"
          }
        ],
        "milestones": [
          {
            "id": "M1",
            "description": "Deliver website page source files.",
            "deadline": "2027-01-22",
            "deliverable_ids": [
              "D1"
            ]
          },
          {
            "id": "M2",
            "description": "Deliver deployment documentation.",
            "deadline": "2027-01-29",
            "deliverable_ids": [
              "D2"
            ]
          }
        ]
      }
    }
  },
  "content_digest": "a5a654b7c201b9eb9fe502b3f8b6a29d503dbc7a94c32680fb1a6a7173cf2a0d",
  "created_at": "2026-11-10T08:03:07.926731Z",
  "payload_json": "{\"draft_id\":\"c15d4d4f-30ef-4852-97f9-dcaa5587a9c0\",\"original_agreement_id\":\"SYNTHETIC-AGREEMENT-1\",\"original_agreement_version\":1,\"project_id\":\"SYNTHETIC-WEB-001\",\"assessment_id\":\"387d0187-adb0-44d7-a275-23647fa86b97\",\"assessment_version\":1,\"original_facts\":{\"project_id\":\"SYNTHETIC-WEB-001\",\"title\":\"Fictional bakery website\",\"client\":{\"id\":\"TEST-CLIENT-1\",\"name\":\"Example Bakery (Synthetic)\"},\"freelancer\":{\"id\":\"TEST-FREELANCER-1\",\"name\":\"Example Developer (Synthetic)\"},\"scope\":\"Build a responsive three-page bakery website using client-supplied copy and images.\",\"budget\":\"1200.00\",\"currency\":\"USD\",\"start_date\":\"2027-01-04\",\"deadline\":\"2027-01-29\",\"deliverables\":[{\"id\":\"D1\",\"description\":\"Home, menu and contact page source files.\",\"deadline\":\"2027-01-22\"},{\"id\":\"D2\",\"description\":\"Website deployment instructions.\",\"deadline\":\"2027-01-29\"}],\"milestones\":[{\"id\":\"M1\",\"description\":\"Deliver website page source files.\",\"deadline\":\"2027-01-22\",\"deliverable_ids\":[\"D1\"]},{\"id\":\"M2\",\"description\":\"Deliver deployment documentation.\",\"deadline\":\"2027-01-29\",\"deliverable_ids\":[\"D2\"]}]},\"version\":\"4\",\"status\":\"PROPOSED_DRAFT\",\"notice\":\"PROPOSED AMENDMENT — NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE\",\"request_snapshot\":{\"original_agreement\":{\"agreement_id\":\"SYNTHETIC-AGREEMENT-1\",\"version\":1,\"project\":{\"project_id\":\"SYNTHETIC-WEB-001\",\"title\":\"Fictional bakery website\",\"client\":{\"id\":\"TEST-CLIENT-1\",\"name\":\"Example Bakery (Synthetic)\"},\"freelancer\":{\"id\":\"TEST-FREELANCER-1\",\"name\":\"Example Developer (Synthetic)\"},\"scope\":\"Build a responsive three-page bakery website using client-supplied copy and images.\",\"budget\":\"1200.00\",\"currency\":\"USD\",\"start_date\":\"2027-01-04\",\"deadline\":\"2027-01-29\",\"deliverables\":[{\"id\":\"D1\",\"description\":\"Home, menu and contact page source files.\",\"deadline\":\"2027-01-22\"},{\"id\":\"D2\",\"description\":\"Website deployment instructions.\",\"deadline\":\"2027-01-29\"}],\"milestones\":[{\"id\":\"M1\",\"description\":\"Deliver website page source files.\",\"deadline\":\"2027-01-22\",\"deliverable_ids\":[\"D1\"]},{\"id\":\"M2\",\"description\":\"Deliver deployment documentation.\",\"deadline\":\"2027-01-29\",\"deliverable_ids\":[\"D2\"]}]}},\"reviewed_assessment\":{\"assessment_id\":\"387d0187-adb0-44d7-a275-23647fa86b97\",\"version\":1,\"agreement_id\":\"SYNTHETIC-AGREEMENT-1\",\"agreement_version\":1,\"assessment\":{\"version\":\"3\",\"request_id\":\"f4ba1f4f-b127-424e-af83-59fb6118d767\",\"project_id\":\"SYNTHETIC-WEB-001\",\"input_snapshot\":{\"request_id\":\"f4ba1f4f-b127-424e-af83-59fb6118d767\",\"project_id\":\"SYNTHETIC-WEB-001\",\"original_project\":{\"project_id\":\"SYNTHETIC-WEB-001\",\"title\":\"Fictional bakery website\",\"client\":{\"id\":\"TEST-CLIENT-1\",\"name\":\"Example Bakery (Synthetic)\"},\"freelancer\":{\"id\":\"TEST-FREELANCER-1\",\"name\":\"Example Developer (Synthetic)\"},\"scope\":\"Build a responsive three-page bakery website using client-supplied copy and images.\",\"budget\":\"1200.00\",\"currency\":\"USD\",\"start_date\":\"2027-01-04\",\"deadline\":\"2027-01-29\",\"deliverables\":[{\"id\":\"D1\",\"description\":\"Home, menu and contact page source files.\",\"deadline\":\"2027-01-22\"},{\"id\":\"D2\",\"description\":\"Website deployment instructions.\",\"deadline\":\"2027-01-29\"}],\"milestones\":[{\"id\":\"M1\",\"description\":\"Deliver website page source files.\",\"deadline\":\"2027-01-22\",\"deliverable_ids\":[\"D1\"]},{\"id\":\"M2\",\"description\":\"Deliver deployment documentation.\",\"deadline\":\"2027-01-29\",\"deliverable_ids\":[\"D2\"]}]},\"client_request\":\"Add an online ordering system with payment integration.\",\"supporting_context\":[]},\"analysis\":{\"classification\":\"OUT_OF_SCOPE\",\"explanation\":\"Online ordering and payment integration appear to add functionality beyond the described website and page source deliverables.\",\"source_references\":[{\"reference\":\"original.scope\",\"excerpt\":\"Build a responsive three-page bakery website using client-supplied copy and images.\"},{\"reference\":\"original.deliverables/0/description\",\"excerpt\":\"Home, menu and contact page source files.\"}],\"requested_changes\":[{\"description\":\"Add online ordering with payment integration.\",\"request_evidence\":{\"reference\":\"request.client_request\",\"excerpt\":\"Add an online ordering system with payment integration.\"},\"source_references\":[{\"reference\":\"original.scope\",\"excerpt\":\"Build a responsive three-page bakery website using client-supplied copy and images.\"}]}],\"potential_impacts\":[{\"category\":\"DELIVERABLES\",\"explanation\":\"Additional ordering functionality could expand the agreed deliverables.\",\"source_references\":[{\"reference\":\"original.deliverables/0/description\",\"excerpt\":\"Home, menu and contact page source files.\"}]},{\"category\":\"TIMELINE\",\"explanation\":\"The implementation effort could affect the project timeline; review is needed.\",\"source_references\":[{\"reference\":\"original.deadline\",\"excerpt\":\"2027-01-29\"}]},{\"category\":\"COMPENSATION\",\"explanation\":\"Additional effort could require a compensation discussion, subject to human review.\",\"source_references\":[{\"reference\":\"original.budget\",\"excerpt\":\"1200.00\"}]}],\"clarification_questions\":[],\"context_references\":[]},\"recommended_action\":\"PROPOSE_AMENDMENT\",\"human_review_required\":true,\"semantic_review_required\":true,\"deterministic_validation\":\"passed; semantic correctness not established\"}},\"review_reference\":\"synthetic-review:387d0187-adb0-44d7-a275-23647fa86b97\"},\"verified_review\":{\"review_reference\":\"synthetic-review:387d0187-adb0-44d7-a275-23647fa86b97\",\"reviewer_reference\":\"SYNTHETIC-REVIEWER\",\"assessment_id\":\"387d0187-adb0-44d7-a275-23647fa86b97\",\"assessment_version\":1,\"agreement_id\":\"SYNTHETIC-AGREEMENT-1\",\"agreement_version\":1,\"agreement_digest\":\"ac4a926786032a9aaf1a6ad2d2be357a3c096d8ad66205e6305b2078caef9948\",\"assessment_digest\":\"6db9b643fb1dbffd93b3218a2dd925e158ecebd86b9b5403da12039598620fe6\",\"reviewed_at\":\"2026-11-10T08:03:07.872322Z\",\"decision\":\"AUTHORIZE_DRAFT_GENERATION\",\"verification_boundary\":\"SYNTHETIC-TEST-REVIEW-STORE\"},\"proposals\":{\"changes\":[{\"change_index\":0,\"additional_scope\":{\"text\":\"The proposed additional work could include online ordering with payment integration, subject to negotiation.\",\"citations\":[{\"reference\":\"agreement.scope\",\"excerpt\":\"Build a responsive three-page bakery website using client-supplied copy and images.\"},{\"reference\":\"request.client_request\",\"excerpt\":\"Add an online ordering system with payment integration.\"},{\"reference\":\"assessment.requested_changes/0/description\",\"excerpt\":\"Add online ordering with payment integration.\"}]},\"deliverable_proposal\":{\"text\":\"A proposed deliverable could cover online ordering with payment integration, subject to negotiation.\",\"citations\":[{\"reference\":\"agreement.scope\",\"excerpt\":\"Build a responsive three-page bakery website using client-supplied copy and images.\"},{\"reference\":\"request.client_request\",\"excerpt\":\"Add an online ordering system with payment integration.\"},{\"reference\":\"assessment.requested_changes/0/description\",\"excerpt\":\"Add online ordering with payment integration.\"}]}}],\"timeline\":{\"text\":\"The additional work may affect the existing project timeline and requires human review before any deadline change.\",\"citations\":[{\"reference\":\"agreement.deadline\",\"excerpt\":\"2027-01-29\"},{\"reference\":\"request.client_request\",\"excerpt\":\"Add an online ordering system with payment integration.\"},{\"reference\":\"assessment.explanation\",\"excerpt\":\"Online ordering and payment integration appear to add functionality beyond the described website and page source deliverables.\"}]},\"compensation\":{\"text\":\"The additional work may affect compensation and requires human review before any change.\",\"citations\":[{\"reference\":\"agreement.budget\",\"excerpt\":\"1200.00\"},{\"reference\":\"request.client_request\",\"excerpt\":\"Add an online ordering system with payment integration.\"},{\"reference\":\"assessment.explanation\",\"excerpt\":\"Online ordering and payment integration appear to add functionality beyond the described website and page source deliverables.\"}]}},\"unresolved_terms\":[\"additional_scope_confirmation\",\"proposed_deliverable_details\",\"revised_timeline\",\"additional_compensation\",\"governing_law\",\"intellectual_property_ownership\",\"termination_conditions\",\"penalties\",\"payment_schedule\",\"acceptance_conditions\",\"other_legal_or_commercial_terms\"],\"human_review_required\":true,\"semantic_review_required\":true,\"effective\":false,\"parties_approved\":false,\"deterministic_validation\":\"passed; semantic correctness not established\",\"rendered_text\":\"PROPOSED CONTRACT AMENDMENT\\nPROPOSED AMENDMENT — NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE\\nDraft reference: c15d4d4f-30ef-4852-97f9-dcaa5587a9c0\\nHUMAN AND SEMANTIC REVIEW REQUIRED; deterministic checks do not prove semantic correctness.\\n\\nORIGINAL AGREEMENT REFERENCE\\nAgreement: SYNTHETIC-AGREEMENT-1; version: 1; project: SYNTHETIC-WEB-001.\\nAssessment: 387d0187-adb0-44d7-a275-23647fa86b97; version: 1.\\nClient: Example Bakery (Synthetic) (TEST-CLIENT-1); freelancer: Example Developer (Synthetic) (TEST-FREELANCER-1).\\n\\nPURPOSE OF AMENDMENT\\nFor negotiation of client-requested work identified in the reviewed scope assessment.\\n\\nEXISTING AGREED FACTS — ORIGINAL SCOPE SUMMARY\\nBuild a responsive three-page bakery website using client-supplied copy and images.\\nOriginal budget: 1200.00 USD; start: 2027-01-04; deadline: 2027-01-29.\\nOriginal deliverable D1: Home, menu and contact page source files. — due 2027-01-22.\\nOriginal deliverable D2: Website deployment instructions. — due 2027-01-29.\\nOriginal milestone M1: Deliver website page source files. — due 2027-01-22; deliverables: D1.\\nOriginal milestone M2: Deliver deployment documentation. — due 2027-01-29; deliverables: D2.\\n\\nCLIENT-REQUESTED CHANGES (NOT AGREED TERMS)\\nAdd an online ordering system with payment integration.\\n\\nPROPOSED ADDITIONAL WORK\\nProposed additional scope remains subject to negotiation and human review.\\nReviewed requested change (not agreed terms): Add online ordering with payment integration.\\n\\nPROPOSED DELIVERABLE CHANGES\\nProposed deliverable specifications remain unresolved and require human review.\\nReviewed requested change (not agreed terms): Add online ordering with payment integration.\\n\\nTIMELINE CONSIDERATIONS\\nTimeline implications require negotiation and human review.\\nNo revised deadline is established by this draft.\\n\\nCOMPENSATION CONSIDERATIONS\\nCompensation implications require negotiation and human review.\\nNo additional amount or payment schedule is established by this draft.\\n\\nUNRESOLVED TERMS\\nAdditional scope confirmation: unresolved — requires negotiation and review.\\nProposed deliverable details: unresolved — requires negotiation and review.\\nRevised timeline: unresolved — requires negotiation and review.\\nAdditional compensation: unresolved — requires negotiation and review.\\nGoverning law: unresolved — requires negotiation and review.\\nIntellectual property ownership: unresolved — requires negotiation and review.\\nTermination conditions: unresolved — requires negotiation and review.\\nPenalties: unresolved — requires negotiation and review.\\nPayment schedule: unresolved — requires negotiation and review.\\nAcceptance conditions: unresolved — requires negotiation and review.\\nOther legal or commercial terms: unresolved — requires negotiation and review.\\n\\nSOURCE CITATIONS\\n[agreement.scope] Build a responsive three-page bakery website using client-supplied copy and images.\\n[request.client_request] Add an online ordering system with payment integration.\\n[assessment.requested_changes/0/description] Add online ordering with payment integration.\\n[agreement.scope] Build a responsive three-page bakery website using client-supplied copy and images.\\n[request.client_request] Add an online ordering system with payment integration.\\n[assessment.requested_changes/0/description] Add online ordering with payment integration.\\n[agreement.deadline] 2027-01-29\\n[request.client_request] Add an online ordering system with payment integration.\\n[assessment.explanation] Online ordering and payment integration appear to add functionality beyond the described website and page source deliverables.\\n[agreement.budget] 1200.00\\n[request.client_request] Add an online ordering system with payment integration.\\n[assessment.explanation] Online ordering and payment integration appear to add functionality beyond the described website and page source deliverables.\\n\\nREVIEW AND APPROVAL NOTICE\\nPROPOSED AMENDMENT — NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE\\nReview of an assessment does not approve this amendment. Neither party's approval is recorded here.\\nThe original agreement is not modified by generating this draft. No signatures or effective date are supplied.\"}"
}
```

</details>

### 5.7 `POST /api/v1/contractflow/amendments/{amendment_id}/register`

Expected digest is the archive digest. Errors:401/403 access or review,404 artifact,409 stale/conflict,422 schema,503 storage.

Synthetic JSON request:

```json
{
  "expected_version": 1,
  "expected_digest": "a5a654b7c201b9eb9fe502b3f8b6a29d503dbc7a94c32680fb1a6a7173cf2a0d"
}
```

<details>
<summary>Complete observed synthetic HTTP 200 JSON response</summary>

```json
{
  "amendment_id": "c15d4d4f-30ef-4852-97f9-dcaa5587a9c0",
  "amendment_version": 1,
  "content_digest": "81f4217aeb223032105f985a8ff7e06e49adfde0e32089da59c786b4866a98df",
  "state": "PENDING_REVIEW",
  "remaining_approvals": [
    "CLIENT",
    "FREELANCER"
  ],
  "human_review_required": true,
  "semantic_review_required": true,
  "effective": false
}
```

</details>

### 5.8 `POST /api/v1/contractflow/amendments/{amendment_id}/decisions`

Expected digest is the V5 subject digest; actor/role comes only from authentication. Errors:401/403,404,409 terminal/state/version/idempotency conflict,422 schema,503 storage.

Synthetic JSON request:

```json
{
  "expected_version": 1,
  "expected_digest": "81f4217aeb223032105f985a8ff7e06e49adfde0e32089da59c786b4866a98df",
  "decision": "APPROVE",
  "idempotency_key": "synthetic-client-audit-example"
}
```

<details>
<summary>Complete observed synthetic HTTP 200 JSON response</summary>

```json
{
  "amendment_id": "c15d4d4f-30ef-4852-97f9-dcaa5587a9c0",
  "amendment_version": 1,
  "content_digest": "81f4217aeb223032105f985a8ff7e06e49adfde0e32089da59c786b4866a98df",
  "state": "PARTIALLY_APPROVED",
  "remaining_approvals": [
    "FREELANCER"
  ],
  "human_review_required": true,
  "semantic_review_required": true,
  "effective": false
}
```

</details>

### 5.9 `GET /api/v1/contractflow/amendments/{amendment_id}/status`

No request body; current trusted review and authorized own-party read required. Errors:401/403/404,409 source conflict where mapped,503 integration.

Request: no JSON body. Executed path: `/api/v1/contractflow/amendments/c15d4d4f-30ef-4852-97f9-dcaa5587a9c0/status`.

<details>
<summary>Complete observed synthetic HTTP 200 JSON response</summary>

```json
{
  "amendment_id": "c15d4d4f-30ef-4852-97f9-dcaa5587a9c0",
  "amendment_version": 1,
  "content_digest": "81f4217aeb223032105f985a8ff7e06e49adfde0e32089da59c786b4866a98df",
  "state": "BOTH_APPROVED",
  "remaining_approvals": [],
  "human_review_required": true,
  "semantic_review_required": true,
  "effective": false
}
```

</details>

### 5.10 `GET /api/v1/contractflow/amendments/{amendment_id}/history`

No request body; authorized own-party read required. Audit excludes contract text and rejection reasons. Errors:401/403/404,503 integration.

Request: no JSON body. Executed path: `/api/v1/contractflow/amendments/c15d4d4f-30ef-4852-97f9-dcaa5587a9c0/history`.

<details>
<summary>Complete observed synthetic HTTP 200 JSON response</summary>

```json
[
  {
    "event_id": "d04ceeb8-33a0-477f-aea8-4b8fb52fb393",
    "amendment_id": "c15d4d4f-30ef-4852-97f9-dcaa5587a9c0",
    "amendment_version": 1,
    "content_digest": "81f4217aeb223032105f985a8ff7e06e49adfde0e32089da59c786b4866a98df",
    "actor_id": "TEST-CLIENT-1",
    "role": "CLIENT",
    "action": "CREATED",
    "previous_state": null,
    "new_state": "PENDING_REVIEW",
    "timestamp": "2026-11-10T08:03:08.188363Z",
    "idempotency_reference": null,
    "decision_id": null
  },
  {
    "event_id": "a8bc3d5a-a349-4126-a963-13732559acf5",
    "amendment_id": "c15d4d4f-30ef-4852-97f9-dcaa5587a9c0",
    "amendment_version": 1,
    "content_digest": "81f4217aeb223032105f985a8ff7e06e49adfde0e32089da59c786b4866a98df",
    "actor_id": "TEST-CLIENT-1",
    "role": "CLIENT",
    "action": "APPROVE",
    "previous_state": "PENDING_REVIEW",
    "new_state": "PARTIALLY_APPROVED",
    "timestamp": "2026-11-10T08:03:08.383859Z",
    "idempotency_reference": "0887946bdac68adba9d5000db2ff9fb5c47cb3843495c72ce30f1dee5eab5a17",
    "decision_id": "614e00ad-5091-4818-a94c-ed990422ac01"
  },
  {
    "event_id": "7de409ed-60fd-4901-b5b4-248c760e5fbc",
    "amendment_id": "c15d4d4f-30ef-4852-97f9-dcaa5587a9c0",
    "amendment_version": 1,
    "content_digest": "81f4217aeb223032105f985a8ff7e06e49adfde0e32089da59c786b4866a98df",
    "actor_id": "TEST-FREELANCER-1",
    "role": "FREELANCER",
    "action": "APPROVE",
    "previous_state": "PARTIALLY_APPROVED",
    "new_state": "BOTH_APPROVED",
    "timestamp": "2026-11-10T08:03:08.571401Z",
    "idempotency_reference": "4668b538317b8542d9537ebc5dfca2257ec0a452c897d527f518b2c47a8ef9d4",
    "decision_id": "f221353b-a5c1-4366-85ed-847b868539be"
  }
]
```

</details>


## 6. Database and persistence

### A. Currently implemented storage

`v5/repository.py::InMemoryApprovalRepository` uses immutable records in a Python
dictionary, a threading RLock and no await inside the lock. A synchronous callback
operates on current state; one dictionary replacement commits audit plus state.
Failures restore the old mapping. Supersession and new-cycle creation are atomic.
This is ONE-process, volatile storage; it is not durable or distributed.

`persistence/artifacts.py` implements validating StoredArtifact and the
ArtifactRepository save/load protocol, not a database. The only concrete artifact
store here is tests/v6_support.py::SyntheticArtifacts (dictionary). Its
SyntheticTransactions uses an asyncio lock with snapshot rollback: test-only,
one-loop behavior, not PostgreSQL isolation. Models/digests are not persisted rows.

### B. PostgreSQL integration design — proposed only

| Proposed table | Keys/relationships/constraints | Intended data |
|---|---|---|
| cf_artifacts | PK artifact_id + revision; immutable revision; project index | kind, source/payload JSONB, digest, UTC timestamp |
| cf_approval_heads | PK amendment_id; FK current cf_artifacts revision | Current revision and locking/CAS sequence |
| cf_approval_versions | PK amendment_id + revision; FK artifact | V5 subject digest/state, party/agreement/source/review IDs |
| cf_decisions | PK decision UUID; FK version; unique revision/role, revision/actor, revision/idempotency key | Decision, trusted actor, normalized request identity, restricted reason, UTC time |
| cf_audit | PK event UUID; FK version, optional decision FK; append sequence | Action, previous/new state, actor/role, digest, time, hashed idempotency reference |
| cf_review_checks | PK check UUID; FK version and optional audit | Trusted review/reviewer reference, revision/digest, check/expiry times |

These names come from the design document, not installed tables or SQL models.
Do not invent shared user/project FKs before Core agrees stable IDs/tenancy.
Use one session/UoW and consistent locks across current artifact/head, source and
agreement version, memberships/permissions and current reviews. Recompute digests,
validate the request and atomically write state, decision, idempotency, audit and
review-check metadata. Serialize review/membership revocation and source/revision
publication with decisions. Use DB uniqueness plus row locks or SERIALIZABLE/CAS;
bound DB-only retries without retrying Groq or external side effects. Restrict
UPDATE/DELETE of audit and published artifacts; define retention/access policy.

### C. Missing production implementation

| Item | ContractFlow checkout | Separate WorkBridge branch |
|---|---|---|
| SQLAlchemy models | Absent | WorkBridge entities exist, not CF artifacts/approvals |
| PostgreSQL repositories | Absent | Absent; inspected database.py configures SQLite |
| Session factory | Absent | Sync SQLite SessionLocal/get_db, not shared CF UoW |
| Alembic migrations | Absent | No Alembic files in branch tree; create_all runs at main import |
| Actual database connection | None opened/tested for CF | Code inspected only; app not imported or run |
| Persistent approval records | Absent | No digest-bound CF dual-party workflow tables |
| Real multi-process approval safety | Not implemented/verified | Not established by inspected SQLite application |

Core must supply sessions/base, IDs/tenancy, migration conventions and an approved
CF-owned schema. No shared-table edits, destructive migrations or create_all calls
were performed. Real PostgreSQL multi-session tests must verify uniqueness,
concurrent/conflicting decisions, revocation races, supersession and crash rollback.

## 7. State, review and rendering invariants

| Current cycle | Action | Result |
|---|---|---|
| New valid inactive draft | Register revision 1 | PENDING_REVIEW |
| PENDING_REVIEW | Either distinct authorized party APPROVE | PARTIALLY_APPROVED |
| PARTIALLY_APPROVED | Other party APPROVE same revision/digest | BOTH_APPROVED |
| Pending/partial cycle | Authorized undecided party REJECT | REJECTED |
| Current cycle, including terminal states | Publish changed next revision | Old SUPERSEDED; new PENDING_REVIEW |
| REJECTED/BOTH_APPROVED/SUPERSEDED | New decision | Typed error; identical same-key replay is the no-op exception |

No decision withdrawal/replacement is allowed in a cycle. Keys are unique per
amendment revision across actors. Same normalized request + actor/role replays
return CURRENT status without duplicate events. Changed payload/actor conflicts;
stale version/digest fails before key lookup. Revisions archive old approvals,
never reuse them. The original agreement is never modified.

V5 SHA-256 binds the full V4 artifact and amendment revision using a format tag
contractflow-approval-v1, model_dump(mode=json), sorted JSON keys, compact separators,
ensure_ascii=True, allow_nan=False and UTF-8 bytes. Facts, rendered text, AI proposals,
terms, evidence and receipt are bound; the source manifest is recomputed. V6 archive
hash separately binds kind/version/source/payload. Expected hashes are integrity
assertions, not authorization or signatures.

V4 validates AI claims before professional templates render exact reviewed-change
descriptions and neutral review notices. AI interpretations stay separately in
proposals. Quality filters reject demonstrated fragments but do not prove grammar
or entailment. Legacy text remains byte-identical on read. Changing presentation
or proposals changes digests: publish the next revision, obtain new exact-content
review and both approvals. No silent upgrade/backfill or approval retention occurs.

V4 ReviewVerifier must resolve current trusted assessment review; V6 AmendmentReviews
must return human+semantic ReviewGrant bound to exact amendment UUID/revision/V5
digest, with UTC review/expiry and revoked=false. V6 rechecks current artifact,
source and both reviews during registration/decision/read paths. Real reviewer
authority, storage and revocation isolation are missing adapters, not production
features established by synthetic reviewers. No request-body flag bypass exists.

## 8. Fresh tests and verification

Executed for this report from the repository root, without dependency installation:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -B -m pytest backend/app/modules/contractflow/tests -p no:cacheprovider -q --tb=short
```

Exact result: **902 passed, 1 warning in 32.49s**; **0 failed, 0 skipped**.
The installed Starlette TestClient warns that httpx usage is deprecated in favor
of httpx2. Dependencies were not changed to suppress it. No coverage-percentage
run or claim; no actual PostgreSQL, real session/auth or real WorkBridge call.

The report also executes demo_v5.run_demo offline: PENDING_REVIEW → PARTIALLY_APPROVED
→ BOTH_APPROVED; two decision events; next revision PENDING_REVIEW; stale attempt
REJECTED_STALE_VERSION; rejection REJECTED; later approval refused; effective=false
and original_agreement_unchanged=true. The eight schema-validated HTTP examples
require nine successful calls including the second party decision and four fake
provider calls. External SDK/HTTP connection paths are blocked for that execution.

Syntax command (executed with no bytecode output):

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
@'
import ast
from pathlib import Path
paths = list(Path("backend/app/modules/contractflow").rglob("*.py"))
for path in paths:
    ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
print(len(paths), "Python files parsed")
'@ | python -B -
```

Result: **107 Python files parsed**. Tracked whitespace is checked with
`git diff --check`; the new untracked report is checked with
`git diff --no-index --check -- /dev/null backend/app/modules/contractflow/CONTRACTFLOW_IMPLEMENTATION_REPORT.md`.
Report paths, links, route/schema matches, complete example payloads and credential
patterns are validated before delivery. No other file is intentionally changed.

| Category | Evidence | Scope |
|---|---|---|
| V1/config/provider | tests/test_service.py, tests/test_schemas.py, tests/test_config.py, tests/test_groq_adapter.py | Immutable facts, fake SDK, failures/timeouts |
| V2 | tests/test_v2_service.py, tests/test_v2_validation.py, tests/test_v2_render.py | Paraphrases, source coverage, review flags |
| V3 | tests/test_v3_service.py, tests/test_v3_quantity_claims.py, tests/test_v3_timeline.py | Classification, local evidence, counts/dates/obligations |
| V4 | tests/test_v4_pipeline.py, tests/test_v4_evidence_diagnostics.py, tests/test_v4_vocabulary.py | Trusted receipts, exact citations and diagnostics |
| V4 rendering | tests/test_v4_professional_rendering.py, tests/test_v4_notice_spacing.py | Templates, notices, mutation rejection and legacy hashes |
| V5 | tests/test_v5_workflow.py | Spoofing, idempotency, threads, rollback, audit/order, revisions |
| V6 | tests/test_v6_api.py, tests/test_v6_integration.py, tests/test_v6_boundaries.py | ASGI workflow, fake storage/UoW, denied/revoked review, stale source |
| Live runner tests | tests/test_live_test_v2.py, tests/test_live_test_v3.py, tests/test_live_test_v4.py | Mocked runner/error reporting, not live calls |

Historically, the user reported successful V1–V4 Groq verification, including V4
DETERMINISTIC_CHECKS_PASSED with openai/gpt-oss-120b. No raw retained response proves
the current professional-renderer live quality. **No live Groq or PayPal request
was made for this audit.** Git remote reads/fetches are not application E2E tests.
Earlier README/V6_HANDOFF test figures describe earlier development snapshots.

Inspected top-level package versions: fastapi 0.141.1, pydantic 2.13.4, groq 1.7.0, pytest 9.1.1, httpx 0.28.1.
No verified dependency manifest/lockfile exists on this branch. WorkBridge's
separate backend/requirements.txt is not a drop-in CF dependency manifest and omits
the Groq/Pytest requirements. No dependencies were installed during this audit.

## 9. Available Core/WorkBridge architecture and compatibility

Core feature/core-platform and main contain LICENSE only. No shared factory,
auth/session API, PostgreSQL base, ID model, error envelope or migrations could be
inspected there. That does not prove no unpushed/external Core implementation exists.

WorkBridge was inspected at its immutable remote commit, never checked out or run:

- [WorkBridge main.py](https://github.com/Omcodesk/Freelanker/blob/d5e7af5f1038f5da782f4377cf1dfc446baedee8/backend/main.py): standalone FastAPI app, import-time create_all, uploads, broad CORS and project/task/milestone/deliverable hooks.
- [WorkBridge database.py](https://github.com/Omcodesk/Freelanker/blob/d5e7af5f1038f5da782f4377cf1dfc446baedee8/backend/database.py): synchronous engine/SessionLocal/get_db for local SQLite.
- [WorkBridge models.py](https://github.com/Omcodesk/Freelanker/blob/d5e7af5f1038f5da782f4377cf1dfc446baedee8/backend/models.py): Project, ProjectMember, Task, Milestone, Comment, Deliverable, Notification.
- [WorkBridge schemas.py](https://github.com/Omcodesk/Freelanker/blob/d5e7af5f1038f5da782f4377cf1dfc446baedee8/backend/schemas.py): name/role and float-amount request fields, not authenticated approval evidence.

| Actual upstream mismatch | Integration consequence | Required decision |
|---|---|---|
| Integer project IDs, party names and member roles, no authenticated user FK | Names/role strings do not prove identity/ownership | Core supplies stable user IDs and memberships |
| Float budget, no currency | Cannot infer exact Decimal budget/currency | Agree precision, currency and authoritative migration; no defaults |
| No project start/deadline or immutable scope/source version | Incomplete ProjectInput/SourceSnapshot | Add authoritative requirements and versioned original agreements |
| Deliverable upload title/file/version, no planned deadline/description | Upload revision is not planned contract deliverable | Agree explicit planned-deliverable mapping, never invent deadlines |
| Milestone due_date string/payment amount, no deliverable_ids | Payout schedule is not CF's delivery milestone | Define valid dates/links; do not introduce payment obligations |
| contract_ref is a mutable string | Not agreement ID/version/digest | Define authoritative immutable agreement registry |
| Inspected routes depend on get_db, not auth | Caller names/roles cannot authorize CF actions | Core protects routes/hooks and supplies auth |
| Sync SQLite, per-handler commits and import-time create_all | Not shared PostgreSQL transaction/migration policy | Agree sessions/base/UoW/Alembic before production |
| Existing React frontend calls WorkBridge's own APIs | No current CF frontend consumption | Teammate connects authenticated CF endpoints |
| POST /api/contracts/approved creates a project; CF drafting needs source project facts first | Bootstrap/lifecycle mismatch | Decide where pre-contract requirements live, avoid circular integration |
| GET /api/milestones/approved advertises payout handoff | Not CF amendment execution or payment authority | Keep separate from BOTH_APPROVED; no automatic hook/payment call |

WorkBridge's approval hook is real code, but not a completed trustworthy CF
integration. No hook was invoked. No actual merge/conflict simulation was run.
Branch trees mainly add distinct paths (flat backend/main.py/database.py/models.py
versus backend/app/modules/contractflow/), so no direct shared-file edit conflict
is demonstrated. Architectural mismatches remain: absolute imports, app lifecycle,
sync/async sessions, schema gaps, error/CORS conventions and approval semantics.

## 10. Core Platform integration matrix

| Dependency | ContractFlow provides | Core/team must provide | Integration status | Risk |
|---|---|---|---|---|
| Shared FastAPI factory | Exported api/router.py router | Actual owned factory/startup/lifespan | PENDING | Core ref has none; WB app is standalone |
| Router mounting | Eight /api/v1/contractflow handlers | Mount once and agree prefix | PENDING | Unmounted handlers are not running APIs |
| Runtime injection | IntegrationRuntime in integrations/workflow.py | auth, workbridge, artifacts, approval_repository, reviews, assessment_reviews, transactions, provider | PARTIALLY COMPLETED | No implicit production enable/fallback |
| Identity | SharedAuth and api/dependencies.py | Real session/token verification and Principal mapping | PARTIALLY COMPLETED | Synthetic contexts/names are not auth |
| Authorization | SharedAuth.authorize, IntegrationActorResolver, v5/authorization.py | Current own-party memberships and read/write permissions | PARTIALLY COMPLETED | Cross-project/spoofed/delegated approvals |
| WorkBridge mapping | WorkBridgeSource.load and SourceSnapshot | Complete authoritative data and agreement/source versions | PARTIALLY COMPLETED | Dates/currency/stable identities missing upstream |
| Source consistency | Expected versions, snapshot equality, post-AI source check | Recheck at commit and inside approval transaction | PARTIALLY COMPLETED | Independent preflight has TOCTOU race |
| PostgreSQL sessions/migrations | Repository contracts and design | Shared base/session, IDs, tenancy, migrations | PENDING | SQLite/create_all is not equivalent |
| Artifact storage | ArtifactRepository and StoredArtifact | Immutable durable save/load with authorization/freshness | PARTIALLY COMPLETED | Keep payload/source/digest bound |
| Approval storage | v5 ApprovalRepository | Durable versions, unique decisions/keys and append-only audit | PARTIALLY COMPLETED | Memory is volatile/process-local |
| Trusted review | V4 ReviewVerifier, AmendmentReviews/ReviewGrant | Reviewer authority, exact-content evidence, expiry/revocation | PARTIALLY COMPLETED | Request flags cannot prove review |
| Transactions/audit | ApprovalTransactions; atomic V5 memory writes | One DB UoW including review-check metadata and revocation | PARTIALLY COMPLETED | Cross-worker races remain unverified |
| Frontend | HTTP schemas/responses | Authenticated consumption/safe rendering | PENDING | No CF frontend implemented |
| Errors/operations | api/errors.py fixed-code responses | Shared envelope, middleware/logging, rate limits, correlation IDs | PARTIALLY COMPLETED | WorkBridge uses HTTPException detail; no Core standard inspected |
| Configuration/provider | GroqSettings, GroqProvider | Secret-managed config, explicit provider/runtime construction | PARTIALLY COMPLETED | No credentials at import or invented DB/auth variables |

In the Core-owned factory, only after real adapters exist:

```python
from backend.app.modules.contractflow.api.router import router

app.state.contractflow_runtime = runtime  # actual complete IntegrationRuntime
app.include_router(router)              # exactly once
```

app/runtime above are integration variables, not existing global objects here.
No production startup command exists until Core supplies that factory. Do not
import tests/v6_support as a production shortcut. All ports must share the actual
transaction context; wrapping independent remote services in a callback is insufficient.

GroqSettings.from_env explicitly reads GROQ_API_KEY and GROQ_MODEL for live calls;
CONTRACTFLOW_TIMEOUT_SECONDS defaults to 30, finite >0 and <=300. No .env loading.
The adapter sends JSON-object mode, temperature 0 and no explicit token limit;
SDK max_retries=0. Offline tests/demo need no key. Missing DB/auth configuration
is adapter-owned and must not be fabricated as existing environment variables.

## 11. Recommended merge and integration sequence

1. Confirm actual Core ownership/interfaces when delivered; agree app factory,
   API prefix, error envelope and lifecycle before editing teammate-owned files.
2. Agree stable identities, pre-contract requirements, source/agreement versions,
   money/currency, project dates and planned deliverables. Resolve the WB bootstrap.
3. Agree shared PostgreSQL/base/session/tenancy/migration strategy; do not use WB's
   import-time create_all as the production migration solution.
4. Connect real auth/authorization and reviewer authority/expiry/revocation policy;
   protect WorkBridge hooks before trusting them.
5. Implement WorkBridgeSource with complete facts. Missing data fails; it is never
   synthesized from names, upload titles, payout amounts or assumed currency.
6. Implement reviewed CF migrations, artifact/V5 repositories, review stores and
   one transaction scope serializing approval with revocation/source revisions.
7. Verify real PostgreSQL multi-session constraints, idempotency, conflicting
   decisions, review/source revocation races, supersession and rollback.
8. Construct real IntegrationRuntime/provider with bounded configuration; mount
   router once. Leave incomplete integration fail-closed.
9. Connect frontend with real sessions and safe display. Do not wire BOTH_APPROVED
   to WorkBridge approved-contract hooks, PayPal, signatures or activation.
10. Run cross-module E2E tests and explicitly authorized synthetic live quality
    review; approve staged rollout only after production blockers are cleared.

## 12. Final integration checklist

- [ ] Core app factory/mount owner identified; router mounted once.
- [ ] Stable client/freelancer identity and own-behalf authorization integrated.
- [ ] Pre-contract project bootstrap and original-agreement registry agreed.
- [ ] WorkBridge precision/currency/dates/deliverable/source-version mapping complete.
- [ ] Shared PostgreSQL sessions/base and reviewed CF migrations implemented.
- [ ] Durable artifacts/approval records with DB uniqueness and immutable revisions.
- [ ] Authorized exact-content review, expiry/revocation and persistent evidence.
- [ ] Shared UoW serializes reviews/memberships/source changes with audit/decisions.
- [ ] Real multi-session PostgreSQL concurrency/rollback tests passed.
- [ ] Frontend/error/logging/rate-limit/correlation policies approved.
- [x] Fresh offline CF suite and schema-validated example workflow passed.
- [x] Syntax, paths, whitespace, credential and documentation-only scope checked.
- [x] No live AI/payment calls, migrations, signatures or amendment activation.
- [ ] Any future activation/payment workflow separately authorized and implemented.

## 13. Sources and final Git state

- [Module README](README.md)
- [V6 handoff](V6_HANDOFF.md), a historical V6 baseline rather than fresh audit figures
- [PostgreSQL design proposal](persistence/POSTGRESQL_DESIGN.md)
- [Router](api/router.py), [HTTP schemas](api/schemas.py), [dependencies](api/dependencies.py), [errors](api/errors.py)
- [Integration contracts](integrations/contracts.py), [runtime](integrations/workflow.py), [artifact interface](persistence/artifacts.py)
- [V5 service](v5/service.py), [repository](v5/repository.py), [states](v5/states.py), [digest](v5/schemas.py)
- [V4 renderer](v4/renderer.py), [quality checks](v4/wording_quality.py), [notice tests](tests/test_v4_notice_spacing.py)

HEAD remains `0608adf2fce1f10d42c62141f38f1a4348e4e7ca` on feature/contractflow. Existing
committed work is synchronized with origin/feature/contractflow; this new report is
untracked/uncommitted and therefore NOT pushed. Pre-existing .venv/, caches and
output/pdf/ remain untouched/untracked. No commit, push, checkout, merge, migration,
Core file edit or production app startup was performed. Read-only remote inspection
updated tracking refs for workbridge and feature/core-platform through git fetch.
