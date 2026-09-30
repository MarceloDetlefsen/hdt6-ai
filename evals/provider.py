"""Proveedor mínimo de Promptfoo para la arquitectura centralizada."""

from __future__ import annotations

import sys
from pathlib import Path

from agents import RunHooks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from centralizada import supervisor  # noqa: E402
from shared.parachute import ToolCallTrace, run_agent  # noqa: E402


class EvalRunHooks(RunHooks):
    """Captura las llamadas reales del Agents SDK, incluidos los as_tools."""

    def __init__(self, trace: ToolCallTrace) -> None:
        self.trace = trace
        self._started: list[int] = []
        self._origins: list[str | None] = []

    async def on_tool_start(self, context, agent, tool) -> None:
        name = getattr(tool, "name", tool.__class__.__name__)
        arguments = getattr(context, "tool_arguments", None)
        try:
            import json

            arguments = json.loads(arguments) if arguments else {}
        except (TypeError, ValueError):
            pass
        agent_name = getattr(agent, "name", agent.__class__.__name__)
        origin = f"agent:{agent_name}"
        previous_origin = self.trace.push_origin(origin)
        index = self.trace.start(name, arguments, origin)
        self._started.append(index)
        self._origins.append(previous_origin)

    async def on_tool_end(self, context, agent, tool, result) -> None:
        if not self._started:
            return
        index = self._started.pop()
        self.trace.finish(index, result=result)
        self.trace.pop_origin(self._origins.pop())


def call_api(prompt, options, context):
    """Ejecuta el agente centralizado con el prompt de Promptfoo."""
    trace = ToolCallTrace()
    hooks = EvalRunHooks(trace)
    with trace.activate():
        respuesta = run_agent(supervisor, prompt, run_hooks=hooks)
    return {"output": respuesta, "metadata": {"tool_calls": trace.tool_calls}}
