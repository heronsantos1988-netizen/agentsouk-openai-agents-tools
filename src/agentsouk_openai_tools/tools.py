"""OpenAI Agents SDK tools backed by the official Agent Souk Python SDK."""
from __future__ import annotations

import json
import os
from typing import Any

from agents import function_tool
from agentsouk import AgentSouk, AgentSoukError


def _client() -> AgentSouk:
    key = os.getenv("AGENTSOUK_API_KEY")
    if not key:
        raise RuntimeError("AGENTSOUK_API_KEY is not set. Use an as_test_ key for sandbox/Base Sepolia.")
    return AgentSouk(api_key=key)


def _loads_object(value: str, field: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field} must decode to a JSON object")
    return parsed


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _run(call) -> str:
    client = _client()
    try:
        return _compact(call(client))
    except AgentSoukError as exc:
        return _compact({
            "ok": False,
            "status": getattr(exc, "status", None),
            "error": getattr(exc, "error", str(exc)),
            "body": getattr(exc, "body", None),
        })
    finally:
        client.close()


# Plain backends make the integration usable outside an LLM loop and easy to test.
def search_listings(query: str, limit: int = 10) -> str:
    limit = max(1, min(int(limit), 50))
    return _run(lambda c: c.listings.search(query, limit=limit))


def create_job(listing_id: str, input_json: str, units: int | None = None) -> str:
    payload = _loads_object(input_json, "input_json")
    return _run(lambda c: c.jobs.create(listing_id, payload, units=units))


def get_job(job_id: str) -> str:
    return _run(lambda c: c.jobs.get(job_id))


def accept_job(job_id: str) -> str:
    return _run(lambda c: c.jobs.accept(job_id))


def deliver_job(job_id: str, output_json: str, message: str = "", preview_json: str = "") -> str:
    output = _loads_object(output_json, "output_json")
    preview = _loads_object(preview_json, "preview_json") if preview_json.strip() else None
    return _run(lambda c: c.jobs.deliver(job_id, output, message=message or None, preview=preview))


def payment_terms(job_id: str) -> str:
    return _run(lambda c: c.jobs.payment_required(job_id))


def get_receipt(job_id: str) -> str:
    return _run(lambda c: c.jobs.receipt(job_id))


def inbox() -> str:
    return _run(lambda c: c.inbox())


def register_agent(name: str, **fields: Any) -> dict[str, Any]:
    """Register outside the LLM tool loop because the response contains secrets.

    Store api_keys and keypair recovery material securely, then expose only
    AGENTSOUK_API_KEY to the runtime that uses these tools.
    """
    return AgentSouk.register(name, **fields)


def pay_gasless(job_id: str, sign_typed_data, operator_confirmed: bool = False) -> str:
    """Pay a job gaslessly through an injected wallet signer.

    The caller must provide an EIP-712 signer and explicitly set
    operator_confirmed=True. This function is intended for host application
    code, not unattended model execution.
    """
    if not operator_confirmed:
        return _compact({
            "ok": False,
            "code": "operator_confirmation_required",
            "message": "Payment was not attempted. Set operator_confirmed=True only after explicit approval.",
        })
    return _run(lambda c: c.jobs.pay_gasless(job_id, sign_typed_data))


def make_agentsouk_pay_gasless_tool(sign_typed_data):
    """Build an optional OpenAI FunctionTool with a host-injected wallet signer."""

    @function_tool(name_override="agentsouk_pay_gasless")
    def _pay(job_id: str, operator_confirmed: bool = False) -> str:
        """Pay a delivered Agent Souk job after explicit operator approval.

        Args:
            job_id: Job id whose current 402 terms should be paid.
            operator_confirmed: Must be true only after the operator approved this payment.
        """
        return pay_gasless(job_id, sign_typed_data, operator_confirmed)

    return _pay


@function_tool
def agentsouk_search_listings(query: str, limit: int = 10) -> str:
    """Search Agent Souk listings.

    Args:
        query: Search words describing the capability needed.
        limit: Maximum results to request, from 1 to 50.
    """
    return search_listings(query, limit)


@function_tool
def agentsouk_create_job(listing_id: str, input_json: str, units: int | None = None) -> str:
    """Create a job from a listing without paying yet.

    Args:
        listing_id: Listing id such as lst_...
        input_json: JSON object matching the listing input schema.
        units: Optional units for per-unit listings.
    """
    return create_job(listing_id, input_json, units)


@function_tool
def agentsouk_get_job(job_id: str) -> str:
    """Read current job state, deadlines, payment state and available actions."""
    return get_job(job_id)


@function_tool
def agentsouk_accept_job(job_id: str) -> str:
    """Accept a job as seller, or accept a revealed delivery as buyer."""
    return accept_job(job_id)


@function_tool
def agentsouk_deliver_job(job_id: str, output_json: str, message: str = "", preview_json: str = "") -> str:
    """Deliver JSON output for a seller job.

    Args:
        job_id: Job id such as job_...
        output_json: Raw JSON object promised by the listing output schema.
        message: Optional delivery note.
        preview_json: Optional JSON object visible before payment.
    """
    return deliver_job(job_id, output_json, message, preview_json)


@function_tool
def agentsouk_payment_terms(job_id: str) -> str:
    """Get payment-required terms for a delivered job without paying."""
    return payment_terms(job_id)


@function_tool
def agentsouk_get_receipt(job_id: str) -> str:
    """Get Agent Souk's signed receipt for a sandbox or live job."""
    return get_receipt(job_id)


@function_tool
def agentsouk_inbox() -> str:
    """Read Agent Souk items that currently require this agent's attention."""
    return inbox()
