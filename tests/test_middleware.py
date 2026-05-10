import logging

import pytest
from fastapi.testclient import TestClient

from app.api.middleware import REQUEST_ID_HEADER


def test_response_includes_a_request_id_header(client: TestClient) -> None:
    response = client.get("/api/health")

    assert REQUEST_ID_HEADER in response.headers
    assert len(response.headers[REQUEST_ID_HEADER]) > 0


def test_inbound_request_id_is_echoed_back(client: TestClient) -> None:
    response = client.get("/api/health", headers={REQUEST_ID_HEADER: "caller-supplied-id"})

    assert response.headers[REQUEST_ID_HEADER] == "caller-supplied-id"


def test_two_requests_get_different_generated_ids(client: TestClient) -> None:
    first = client.get("/api/health")
    second = client.get("/api/health")

    assert first.headers[REQUEST_ID_HEADER] != second.headers[REQUEST_ID_HEADER]


def test_request_completed_log_line_carries_the_real_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/api/health")

    request_id = response.headers[REQUEST_ID_HEADER]
    completion_records = [r for r in caplog.records if r.getMessage() == "request completed"]

    assert len(completion_records) == 1
    # Regression check: the ContextVar used to be reset before this log call, so the request
    # ID filter picked up the "no active request" default (None) instead of the real value.
    assert completion_records[0].request_id == request_id  # type: ignore[attr-defined]
