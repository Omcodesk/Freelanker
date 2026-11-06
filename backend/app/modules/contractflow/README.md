# ContractFlow

ContractFlow is Freelanker's contract module. Person 2 owns only its backend. Freelanker
is a full-stack PayPal + AI freelancing platform.

## Phase 0 scope

This module currently establishes only its package boundary and documentation.
Frontend development and UI integration will be handled by another teammate.
No endpoints, models, business logic, AI calls, or shared infrastructure are
implemented here.

The target stack is React + TypeScript, Python + FastAPI, PostgreSQL +
SQLAlchemy + Alembic, Pydantic, Pytest, and Groq. Shared stack choices and
scaffolding remain subject to team confirmation. This foundation requires no
installed dependencies.

## Responsibilities and future phases

Phase 1 and later may implement the following, in a sequence agreed with the team:

- AI-assisted contract generation and validated AI output.
- Contract management APIs and contract lifecycle rules.
- Dual-party digital acceptance and participant access checks.
- Scope change detection against an agreed contract scope snapshot.
- Amendments and contract version history.
- Module-specific backend tests.

These capabilities are responsibilities only; none are part of Phase 0.

## Dependencies and boundaries

### Core Platform

ContractFlow will depend on authenticated user identity, client/freelancer roles,
participant identifiers, and shared authorization conventions. Core Platform
owns authentication; ContractFlow will enforce access to its own resources.

Reuse team-owned settings, database sessions, API error conventions, logging,
secret handling, and any shared Groq client. Keep Groq credentials on the backend.
ContractFlow will own its prompts and output validation when implemented.
Payment execution and PayPal credentials remain outside this module; any future
payment-status references require an agreed interface.

### WorkBridge

ContractFlow will need agreed project or engagement identifiers, participants,
scope, deliverables, milestones, and commercial terms from WorkBridge.
WorkBridge owns the source project data. ContractFlow will preserve an agreed
snapshot per contract version so later project edits cannot silently change it.

Scope-change inputs and contract-status updates require agreed service or API
interfaces. Do not write directly to WorkBridge-owned tables.

## Ownership

Person 2 owns only this backend module and future backend tests under
`backend/tests/modules/contractflow/`. Another teammate owns frontend development
and UI integration, coordinated through agreed backend API contracts. Future module-specific
migrations must use the team's shared Alembic history and be coordinated.

Shared entry points, dependency manifests, routing, database configuration,
Alembic configuration, authentication, and payment modules are outside this
module's Phase 0 ownership. Do not duplicate that infrastructure here.
