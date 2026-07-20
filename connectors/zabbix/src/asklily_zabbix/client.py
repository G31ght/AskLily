"""A minimal Zabbix JSON-RPC client that permits only explicit read methods."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

ALLOWED_READ_METHODS = frozenset({"host.get", "item.get", "history.get"})


class ConnectorConfigurationError(ValueError):
    """Raised before any transport is created when local configuration is unsafe."""


class ConnectorPolicyError(ValueError):
    """Raised when a caller attempts a method outside the read-only allow-list."""


class ConnectorResponseError(RuntimeError):
    """Raised when a JSON-RPC response is malformed or contains an API error."""


class JsonRpcTransport(Protocol):
    """Injectable transport; tests use a local fake and never perform network I/O."""

    def post(
        self, endpoint: str, headers: Mapping[str, str], body: Mapping[str, object], timeout_seconds: float
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class ZabbixReadOnlyConfig:
    endpoint: str
    api_token: str
    timeout_seconds: float = 5.0

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> ZabbixReadOnlyConfig:
        values = os.environ if environment is None else environment
        endpoint = values.get("ASKLILY_ZABBIX_URL", "").strip()
        token = values.get("ASKLILY_ZABBIX_API_TOKEN", "").strip()
        if not endpoint or not token:
            raise ConnectorConfigurationError("zabbix_local_readonly_configuration_required")
        if not endpoint.startswith("https://"):
            raise ConnectorConfigurationError("zabbix_https_endpoint_required")
        if not endpoint.endswith("api_jsonrpc.php"):
            raise ConnectorConfigurationError("zabbix_jsonrpc_endpoint_required")
        return cls(endpoint=endpoint, api_token=token)


class UrllibJsonRpcTransport:
    """Live transport for a future L4 run; never instantiated by P3 mock tests."""

    def post(
        self, endpoint: str, headers: Mapping[str, str], body: Mapping[str, object], timeout_seconds: float
    ) -> Mapping[str, object]:
        request = Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - endpoint is config-gated
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise ConnectorResponseError("zabbix_transport_or_response_error") from exc
        if not isinstance(payload, dict):
            raise ConnectorResponseError("zabbix_response_not_object")
        return payload


class ZabbixReadOnlyClient:
    """Only exposes the P3 discovery/history calls required for future optic mapping."""

    def __init__(self, config: ZabbixReadOnlyConfig, transport: JsonRpcTransport) -> None:
        self._config = config
        self._transport = transport
        self._request_id = 0

    def list_hosts(self, group_ids: Sequence[str]) -> list[Mapping[str, object]]:
        return self._call(
            "host.get",
            {
                "groupids": list(group_ids),
                "output": ["hostid", "host", "name", "status"],
                "sortfield": "hostid",
            },
        )

    def list_items(self, host_ids: Sequence[str]) -> list[Mapping[str, object]]:
        return self._call(
            "item.get",
            {
                "hostids": list(host_ids),
                "output": ["itemid", "hostid", "key_", "name", "value_type", "lastclock", "status"],
                "sortfield": "itemid",
            },
        )

    def read_history(
        self, item_ids: Sequence[str], *, time_from: int, time_till: int, page_size: int = 100
    ) -> list[Mapping[str, object]]:
        if page_size < 1 or page_size > 1000:
            raise ConnectorPolicyError("zabbix_history_page_size_invalid")
        values: list[Mapping[str, object]] = []
        for index in range(0, len(item_ids), page_size):
            values.extend(
                self._call(
                    "history.get",
                    {
                        "itemids": list(item_ids[index : index + page_size]),
                        "time_from": time_from,
                        "time_till": time_till,
                        "output": "extend",
                        "sortfield": "clock",
                        "sortorder": "DESC",
                        "limit": page_size,
                    },
                )
            )
        return values

    def _call(self, method: str, params: Mapping[str, object]) -> list[Mapping[str, object]]:
        if method not in ALLOWED_READ_METHODS:
            raise ConnectorPolicyError("zabbix_method_not_read_only")
        self._request_id += 1
        response = self._transport.post(
            self._config.endpoint,
            {"Content-Type": "application/json-rpc", "Authorization": f"Bearer {self._config.api_token}"},
            {"jsonrpc": "2.0", "method": method, "params": dict(params), "id": self._request_id},
            self._config.timeout_seconds,
        )
        if "error" in response:
            raise ConnectorResponseError("zabbix_jsonrpc_error")
        result = response.get("result")
        if not isinstance(result, list) or not all(isinstance(item, Mapping) for item in result):
            raise ConnectorResponseError("zabbix_result_not_list")
        return list(result)
