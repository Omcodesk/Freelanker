import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ..schemas import ProjectInput


@pytest.mark.parametrize("name", ["website_project.json", "branding_project.json"])
def test_synthetic_examples(name):
    data = json.loads((Path(__file__).parent / "fixtures" / name).read_text())
    project = ProjectInput.model_validate(data)
    assert project.budget > 0
    assert ProjectInput.model_validate_json(project.model_dump_json()) == project


@pytest.mark.parametrize("field", list(ProjectInput.model_fields))
def test_every_input_field_required(project_data, field):
    del project_data[field]
    with pytest.raises(ValidationError):
        ProjectInput.model_validate(project_data)


@pytest.mark.parametrize("field,value", [
    ("budget", "-1"), ("budget", "NaN"), ("budget", "1.00001"),
    ("currency", "usd"), ("currency", "US"), ("scope", "  "),
    ("deadline", "2026-01-01"), ("deliverables", []), ("milestones", []),
])
def test_invalid_values(project_data, field, value):
    project_data[field] = value
    with pytest.raises(ValidationError):
        ProjectInput.model_validate(project_data)


@pytest.mark.parametrize("case", ["party", "duplicate", "reference", "date", "milestone_date", "extra"])
def test_cross_field_validation(project_data, case):
    if case == "party":
        project_data["freelancer"]["id"] = project_data["client"]["id"]
    elif case == "duplicate":
        project_data["deliverables"].append(project_data["deliverables"][0])
    elif case == "reference":
        project_data["milestones"][0]["deliverable_ids"] = ["UNKNOWN"]
    elif case == "date":
        project_data["deliverables"][0]["deadline"] = "2028-01-01"
    elif case == "milestone_date":
        project_data["milestones"][0]["deadline"] = "2027-01-10"
    else:
        project_data["payment_schedule"] = "invented"
    with pytest.raises(ValidationError):
        ProjectInput.model_validate(project_data)
