"""Workflow-facing Protocols.

`backend/workflow/` is a sibling of `backend/agents/` (spec §10) so it
does not import concrete agent classes. The orchestrator constructs the
`AgentRegistry` and passes it in; workflow treats both the registry and
each agent as duck-typed objects matching these Protocols.

In practice `BaseAgent` (and its subclasses) satisfies `WorkflowAgent`,
and `AgentRegistry` satisfies `WorkflowAgentRegistry`, by virtue of
exposing the right method/property names.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WorkflowAgent(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def wallet_id(self) -> str: ...

    @property
    def is_ghost(self) -> bool: ...

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]: ...

    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]: ...


class WorkflowAgentRegistry(Protocol):
    async def get_by_id(self, agent_id: str) -> WorkflowAgent: ...

    async def list_workers(self) -> list[WorkflowAgent]: ...

    async def list_judge(self) -> WorkflowAgent: ...
