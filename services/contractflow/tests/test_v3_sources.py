from ..v3.schemas import ScopeChangeInput
from ..v3.sources import original_sources, untrusted_sources
from .test_v3_schemas import case_input


def test_registries_separate_facts_and_context():
    data = ScopeChangeInput.model_validate(case_input("needs_clarification"))
    original, untrusted = original_sources(data), untrusted_sources(data)
    assert original["original.budget"] == "1200.00"
    assert original["original.currency"] == "USD"
    assert original["original.deadline"] == "2027-01-29"
    assert original["original.deliverables/0/id"] == "D1"
    assert original["original.milestones/0/deliverable_ids/0"] == "D1"
    assert set(original).isdisjoint(untrusted)
    assert untrusted["context/0"] == data.supporting_context[0].text
    assert "original.client.name" not in original
