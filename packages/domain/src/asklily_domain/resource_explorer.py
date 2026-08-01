"""Scope-safe Fixture resource directory for the P5G read-only workspace.

The directory deliberately owns only public resource navigation data.  Optical
health remains owned by :mod:`asklily_domain.optic_health`; callers can attach
its already-evaluated conclusion without importing observations or events into
the resource identity model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from asklily_contracts import Resource, Scope

RESOURCE_EXPLORER_SOURCE = "fixture://resource-explorer/l0-l1-v1"
OPTIC_MODULE_TYPE = "optic_module"
RESOURCE_PAGE_SIZE = 20
RESOURCE_SUGGESTION_LIMIT = 10
ALLOWED_RESOURCE_TYPES = frozenset({"site", "device", "interface", OPTIC_MODULE_TYPE})
_QUERY_PATTERN = re.compile(r"^[\w\s\-.]+$", re.UNICODE)


@dataclass(frozen=True)
class ResourceDirectoryRecord:
    """A Fixture-only public directory entry and its static relationships."""

    resource: Resource
    summary: str
    attributes: dict[str, str]
    related_resource_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResourceSearchPage:
    """Server-paginated public summaries; no observations or events are present."""

    items: tuple[ResourceDirectoryRecord, ...]
    page: int
    page_size: int
    total: int

    @property
    def has_more(self) -> bool:
        return self.page * self.page_size < self.total


def _resource(
    resource_id: str,
    resource_type: str,
    display_name: str,
    site_id: str,
) -> Resource:
    return Resource(
        resource_id=resource_id,
        project_id="demo-project",
        resource_type=resource_type,
        display_name=display_name,
        site_id=site_id,
        source_ref=RESOURCE_EXPLORER_SOURCE,
    )


# Stable Fixture identities deliberately use invented labels only.  The optic
# IDs match the P2 health Fixture so P5G can reference existing conclusions.
FIXTURE_DIRECTORY = (
    ResourceDirectoryRecord(_resource("site-a", "site", "Site A", "site-a"), "Fixture site A", {"site_name": "Site A"}, ("leaf-a01", "leaf-a02", "leaf-a03")),
    ResourceDirectoryRecord(_resource("site-b", "site", "Site B", "site-b"), "Fixture site B", {"site_name": "Site B"}, ("leaf-b01",)),
    ResourceDirectoryRecord(_resource("leaf-a01", "device", "leaf-a01", "site-a"), "Fixture leaf device", {"device_role": "leaf"}, ("site-a", "interface-a01-e1-1", "interface-a01-e1-2", "interface-a01-e1-3")),
    ResourceDirectoryRecord(_resource("leaf-a02", "device", "leaf-a02", "site-a"), "Fixture leaf device", {"device_role": "leaf"}, ("site-a", "interface-a02-e1-1", "interface-a02-e1-2", "interface-a02-e1-3")),
    ResourceDirectoryRecord(_resource("leaf-a03", "device", "leaf-a03", "site-a"), "Fixture leaf device", {"device_role": "leaf"}, ("site-a", "interface-a03-e1-1")),
    ResourceDirectoryRecord(_resource("leaf-b01", "device", "leaf-b01", "site-b"), "Fixture leaf device", {"device_role": "leaf"}, ("site-b", "interface-b01-e1-1")),
    ResourceDirectoryRecord(_resource("interface-a01-e1-1", "interface", "leaf-a01 / Ethernet1/1", "site-a"), "Fixture device interface", {"interface_name": "Ethernet1/1"}, ("site-a", "leaf-a01", "optic-a-01")),
    ResourceDirectoryRecord(_resource("interface-a01-e1-2", "interface", "leaf-a01 / Ethernet1/2", "site-a"), "Fixture device interface", {"interface_name": "Ethernet1/2"}, ("site-a", "leaf-a01", "optic-a-02")),
    ResourceDirectoryRecord(_resource("interface-a01-e1-3", "interface", "leaf-a01 / Ethernet1/3", "site-a"), "Fixture device interface", {"interface_name": "Ethernet1/3"}, ("site-a", "leaf-a01", "optic-a-03")),
    ResourceDirectoryRecord(_resource("interface-a02-e1-1", "interface", "leaf-a02 / Ethernet1/1", "site-a"), "Fixture device interface", {"interface_name": "Ethernet1/1"}, ("site-a", "leaf-a02", "optic-a-04")),
    ResourceDirectoryRecord(_resource("interface-a02-e1-2", "interface", "leaf-a02 / Ethernet1/2", "site-a"), "Fixture device interface", {"interface_name": "Ethernet1/2"}, ("site-a", "leaf-a02", "optic-a-05")),
    ResourceDirectoryRecord(_resource("interface-a02-e1-3", "interface", "leaf-a02 / Ethernet1/3", "site-a"), "Fixture device interface", {"interface_name": "Ethernet1/3"}, ("site-a", "leaf-a02", "optic-a-06")),
    ResourceDirectoryRecord(_resource("interface-a03-e1-1", "interface", "leaf-a03 / Ethernet1/1", "site-a"), "Fixture device interface", {"interface_name": "Ethernet1/1"}, ("site-a", "leaf-a03", "optic-a-07")),
    ResourceDirectoryRecord(_resource("interface-b01-e1-1", "interface", "leaf-b01 / Ethernet1/1", "site-b"), "Fixture device interface", {"interface_name": "Ethernet1/1"}, ("site-b", "leaf-b01", "optic-b-01")),
    ResourceDirectoryRecord(_resource("optic-a-01", OPTIC_MODULE_TYPE, "optic-a-01", "site-a"), "Fixture optic module on leaf-a01 / Ethernet1/1", {"interface_name": "Ethernet1/1"}, ("site-a", "leaf-a01", "interface-a01-e1-1")),
    ResourceDirectoryRecord(_resource("optic-a-02", OPTIC_MODULE_TYPE, "optic-a-02", "site-a"), "Fixture optic module on leaf-a01 / Ethernet1/2", {"interface_name": "Ethernet1/2"}, ("site-a", "leaf-a01", "interface-a01-e1-2")),
    ResourceDirectoryRecord(_resource("optic-a-03", OPTIC_MODULE_TYPE, "optic-a-03", "site-a"), "Fixture optic module on leaf-a01 / Ethernet1/3", {"interface_name": "Ethernet1/3"}, ("site-a", "leaf-a01", "interface-a01-e1-3")),
    ResourceDirectoryRecord(_resource("optic-a-04", OPTIC_MODULE_TYPE, "optic-a-04", "site-a"), "Fixture optic module on leaf-a02 / Ethernet1/1", {"interface_name": "Ethernet1/1"}, ("site-a", "leaf-a02", "interface-a02-e1-1")),
    ResourceDirectoryRecord(_resource("optic-a-05", OPTIC_MODULE_TYPE, "optic-a-05", "site-a"), "Fixture optic module on leaf-a02 / Ethernet1/2", {"interface_name": "Ethernet1/2"}, ("site-a", "leaf-a02", "interface-a02-e1-2")),
    ResourceDirectoryRecord(_resource("optic-a-06", OPTIC_MODULE_TYPE, "optic-a-06", "site-a"), "Fixture optic module on leaf-a02 / Ethernet1/3", {"interface_name": "Ethernet1/3"}, ("site-a", "leaf-a02", "interface-a02-e1-3")),
    ResourceDirectoryRecord(_resource("optic-a-07", OPTIC_MODULE_TYPE, "optic-a-07", "site-a"), "Fixture optic module on leaf-a03 / Ethernet1/1", {"interface_name": "Ethernet1/1"}, ("site-a", "leaf-a03", "interface-a03-e1-1")),
    ResourceDirectoryRecord(_resource("optic-b-01", OPTIC_MODULE_TYPE, "optic-b-01", "site-b"), "Fixture optic module on leaf-b01 / Ethernet1/1", {"interface_name": "Ethernet1/1"}, ("site-b", "leaf-b01", "interface-b01-e1-1")),
)

_DIRECTORY_BY_ID = {item.resource.resource_id: item for item in FIXTURE_DIRECTORY}


def validate_resource_query(query: str) -> str:
    """Accept small literal lookup text only; patterns, URLs and paths fail closed."""
    normalized = " ".join(query.split())
    if not normalized or len(normalized) > 100 or not _QUERY_PATTERN.fullmatch(normalized):
        raise ValueError("resource_search_query_invalid")
    return normalized.casefold()


def visible_resource_records(scope: Scope) -> tuple[ResourceDirectoryRecord, ...]:
    """Return only directory entries visible in the supplied server Scope."""
    return tuple(record for record in FIXTURE_DIRECTORY if _visible(record.resource, scope))


def search_resources(
    scope: Scope,
    *,
    query: str | None = None,
    site_id: str | None = None,
    resource_type: str | None = None,
    resource_ids: frozenset[str] | None = None,
    page: int = 1,
    page_size: int = RESOURCE_PAGE_SIZE,
) -> ResourceSearchPage:
    """Search visible Fixture metadata and paginate on the server."""
    if page < 1 or page_size != RESOURCE_PAGE_SIZE:
        raise ValueError("resource_search_pagination_invalid")
    if resource_type is not None and resource_type not in ALLOWED_RESOURCE_TYPES:
        raise ValueError("resource_type_invalid")
    normalized_query = validate_resource_query(query) if query is not None else None
    matches = [
        record
        for record in visible_resource_records(scope)
        if (resource_ids is None or record.resource.resource_id in resource_ids)
        and _matches(record, normalized_query, site_id, resource_type)
    ]
    matches.sort(key=lambda record: (record.resource.resource_type, record.resource.resource_id))
    start = (page - 1) * page_size
    return ResourceSearchPage(tuple(matches[start : start + page_size]), page, page_size, len(matches))


def resource_detail(scope: Scope, resource_id: str) -> ResourceDirectoryRecord | None:
    """Return ``None`` for both an unknown and a Scope-hidden resource."""
    record = _DIRECTORY_BY_ID.get(resource_id)
    return record if record is not None and _visible(record.resource, scope) else None


def related_resources(record: ResourceDirectoryRecord, scope: Scope) -> tuple[ResourceDirectoryRecord, ...]:
    """Project static relationships through the same Scope as the focus entry."""
    return tuple(
        related
        for resource_id in record.related_resource_ids
        if (related := resource_detail(scope, resource_id)) is not None
    )


def _visible(resource: Resource, scope: Scope) -> bool:
    return (
        resource.project_id == scope.project_id
        and (not scope.site_ids or resource.site_id in scope.site_ids)
        and (not scope.resource_types or resource.resource_type in scope.resource_types)
    )


def _matches(
    record: ResourceDirectoryRecord,
    normalized_query: str | None,
    site_id: str | None,
    resource_type: str | None,
) -> bool:
    resource = record.resource
    if site_id is not None and resource.site_id != site_id:
        return False
    if resource_type is not None and resource.resource_type != resource_type:
        return False
    if normalized_query is None:
        return True
    searchable = f"{resource.resource_id} {resource.display_name} {record.summary}".casefold()
    return normalized_query in searchable
