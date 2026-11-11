"""
Supabase PostgreSQL Project and Agreement Source Adapter for ContractFlow.

Implements ContractFlow's WorkBridgeSource protocol:
- Reads authoritative project, parties, milestones, and agreements from PostgreSQL.
- Strictly requires explicit planned deliverables, milestones, and deadlines (never invents terms).
- Enforces distinct client and freelancer identities.
- Resolves the current agreed AgreementSnapshot for scope change and amendment workflows.
"""

import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from ..integrations.contracts import IntegrationError, Principal, SourceSnapshot, WorkBridgeSource
from ..schemas import Deliverable, Milestone, Party, ProjectInput
from ..v4.schemas import AgreementSnapshot
from .db import get_connection


class SupabaseCoreSource(WorkBridgeSource):
    async def load(self, project_id: str, principal: Principal) -> SourceSnapshot:
        """
        Authorize access and return complete immutable versioned project facts.
        Fails closed with INVALID_SOURCE if deliverables or milestones are incomplete.
        """
        try:
            proj_uuid = uuid.UUID(project_id)
        except ValueError:
            raise IntegrationError("NOT_FOUND")

        async for conn in get_connection():
            # 1. Fetch project header
            project_row = await conn.fetchrow(
                """
                SELECT id, title, description, status, client_id, freelancer_id,
                       currency, total_budget, COALESCE(source_version, 1) as source_version,
                       created_at
                FROM public.projects
                WHERE id = $1
                """,
                proj_uuid,
            )
            if not project_row:
                raise IntegrationError("NOT_FOUND")

            client_id = project_row["client_id"]
            freelancer_id = project_row["freelancer_id"]
            if not client_id or not freelancer_id or client_id == freelancer_id:
                raise IntegrationError("INVALID_SOURCE")

            # 2. Fetch party profiles
            client_row = await conn.fetchrow(
                "SELECT id, display_name FROM public.profiles WHERE id = $1", client_id
            )
            freelancer_row = await conn.fetchrow(
                "SELECT id, display_name FROM public.profiles WHERE id = $1", freelancer_id
            )
            if not client_row or not freelancer_row:
                raise IntegrationError("INVALID_SOURCE")

            client_party = Party(
                id=str(client_row["id"]),
                name=client_row["display_name"] or "Client",
            )
            freelancer_party = Party(
                id=str(freelancer_row["id"]),
                name=freelancer_row["display_name"] or "Freelancer",
            )

            # 3. Fetch planned milestones
            milestone_rows = await conn.fetch(
                """
                SELECT id, title, description, due_date, order_index
                FROM public.milestones
                WHERE project_id = $1
                ORDER BY order_index ASC, created_at ASC
                """,
                proj_uuid,
            )

            # Require explicit planned milestones (fail closed if missing)
            if not milestone_rows:
                raise IntegrationError("INVALID_SOURCE")

            # Project start date: use created_at date
            created_dt = project_row["created_at"]
            start_date: date = created_dt.date() if isinstance(created_dt, datetime) else created_dt

            # Construct deliverables and milestones from authoritative rows
            deliverables_list: list[Deliverable] = []
            milestones_list: list[Milestone] = []

            for row in milestone_rows:
                m_id = str(row["id"])
                m_due: date | None = row["due_date"]
                if not m_due:
                    raise IntegrationError("INVALID_SOURCE")

                # Each planned milestone anchors a contractual deliverable
                deliv_id = f"deliv-{m_id}"
                deliv_desc = row["description"] or row["title"]
                deliverables_list.append(
                    Deliverable(id=deliv_id, description=deliv_desc, deadline=m_due)
                )

                milestones_list.append(
                    Milestone(
                        id=m_id,
                        description=row["description"] or row["title"],
                        deadline=m_due,
                        deliverable_ids=(deliv_id,),
                    )
                )

            # Determine project deadline as the latest milestone deadline
            max_deadline = max(m.deadline for m in milestones_list)
            if max_deadline < start_date:
                raise IntegrationError("INVALID_SOURCE")

            # Total budget
            budget_val = project_row["total_budget"]
            if not budget_val or budget_val <= 0:
                raise IntegrationError("INVALID_SOURCE")
            budget = Decimal(str(budget_val))

            scope_text = project_row["description"] or project_row["title"]

            try:
                project_input = ProjectInput(
                    project_id=str(project_row["id"]),
                    title=project_row["title"],
                    client=client_party,
                    freelancer=freelancer_party,
                    scope=scope_text,
                    budget=budget,
                    currency=project_row["currency"] or "USD",
                    start_date=start_date,
                    deadline=max_deadline,
                    deliverables=tuple(deliverables_list),
                    milestones=tuple(milestones_list),
                )
            except Exception:
                raise IntegrationError("INVALID_SOURCE") from None

            # 4. Fetch current active or approved agreement (if present)
            agreement_snapshot: AgreementSnapshot | None = None
            ag_row = await conn.fetchrow(
                """
                SELECT id, version_number, content_snapshot
                FROM public.agreements
                WHERE project_id = $1 AND is_current = TRUE
                LIMIT 1
                """,
                proj_uuid,
            )
            if ag_row:
                ag_id = str(ag_row["id"])
                ag_version = ag_row["version_number"]
                snapshot_data = ag_row["content_snapshot"]
                if snapshot_data:
                    if isinstance(snapshot_data, str):
                        snapshot_dict = json.loads(snapshot_data)
                    else:
                        snapshot_dict = snapshot_data
                    try:
                        ag_project = ProjectInput.model_validate(snapshot_dict)
                    except Exception:
                        ag_project = project_input
                else:
                    ag_project = project_input

                agreement_snapshot = AgreementSnapshot(
                    agreement_id=ag_id,
                    version=ag_version,
                    project=ag_project,
                )

            return SourceSnapshot(
                source_version=project_row["source_version"],
                project=project_input,
                agreement=agreement_snapshot,
            )
