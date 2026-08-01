import pytest
from asklily_contracts import Scope
from asklily_domain import (
    related_resources,
    resource_detail,
    search_resources,
    validate_resource_query,
)

SITE_A_SCOPE = Scope("demo-project", frozenset({"site-a"}), actions=frozenset({"read"}))


def test_directory_exposes_only_stable_fixture_public_metadata_in_scope() -> None:
    result = search_resources(SITE_A_SCOPE, query="leaf-a01")
    resource_ids = {item.resource.resource_id for item in result.items}
    assert "leaf-a01" in resource_ids
    assert "optic-a-02" in resource_ids
    assert "leaf-b01" not in resource_ids
    assert all(item.resource.source_ref == "fixture://resource-explorer/l0-l1-v1" for item in result.items)


def test_hidden_and_unknown_resource_details_are_identically_absent() -> None:
    assert resource_detail(SITE_A_SCOPE, "optic-b-01") is None
    assert resource_detail(SITE_A_SCOPE, "does-not-exist") is None


def test_detail_relationships_are_projected_through_scope() -> None:
    optic = resource_detail(SITE_A_SCOPE, "optic-a-02")
    assert optic is not None
    assert {item.resource.resource_id for item in related_resources(optic, SITE_A_SCOPE)} == {
        "site-a",
        "leaf-a01",
        "interface-a01-e1-2",
    }


def test_directory_rejects_path_or_unknown_type_and_uses_fixed_page_size() -> None:
    with pytest.raises(ValueError, match="resource_search_query_invalid"):
        validate_resource_query("../../secret")
    with pytest.raises(ValueError, match="resource_type_invalid"):
        search_resources(SITE_A_SCOPE, resource_type="router")
    with pytest.raises(ValueError, match="resource_search_pagination_invalid"):
        search_resources(SITE_A_SCOPE, page_size=5)
