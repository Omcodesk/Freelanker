"""Offline synthetic workflow, not authentication, execution or legal approval."""

import asyncio
import json

from .v5.errors import InvalidTransition, StaleVersion


async def run_demo():
    # Synthetic identity and V4 artifact assembly exist ONLY in test support.
    from .tests.v5_support import amendment, decision, initialized

    service, initial = await initialized()
    before = (await service.repository.load(initial.amendment_id)).subject.draft.original_facts
    client = await service.submit_decision(decision(initial, key="demo-client"), "synthetic-client")
    both = await service.submit_decision(decision(initial, key="demo-freelancer"), "synthetic-freelancer")
    history = await service.get_history(initial.amendment_id, "synthetic-client")
    revised = await service.register_amendment(amendment(revised=True), 2, "synthetic-client")
    try:
        await service.submit_decision(decision(initial), "synthetic-client")
    except StaleVersion:
        stale = "REJECTED_STALE_VERSION"
    rejected = await service.submit_decision(decision(revised, choice="REJECT", key="demo-reject",
                                                     reason="Synthetic review needs clarification"), "synthetic-client")
    try:
        await service.submit_decision(decision(revised, key="demo-after-reject"), "synthetic-freelancer")
    except InvalidTransition:
        terminal = "REJECTED_TERMINAL_CYCLE"
    current = await service.repository.load(initial.amendment_id)
    return {"notice": "SYNTHETIC OFFLINE DEMO — NOT REAL AUTHENTICATION, SIGNATURES OR ACTIVATION",
            "initial": initial.model_dump(mode="json"), "client": client.model_dump(mode="json"),
            "both": both.model_dump(mode="json"), "decision_event_count": sum(e.action in {"APPROVE", "REJECT"} for e in history),
            "revised_state": revised.state, "rejection_state": rejected.state,
            "stale_attempt": stale, "approval_after_rejection": terminal,
            "effective": both.effective, "original_agreement_unchanged": before == current.subject.draft.original_facts}


def main():
    print(json.dumps(asyncio.run(run_demo()), indent=2))


if __name__ == "__main__":
    main()
