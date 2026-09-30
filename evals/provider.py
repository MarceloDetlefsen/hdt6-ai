"""Proveedor mínimo de Promptfoo para la arquitectura centralizada."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from centralizada import supervisor  # noqa: E402
from shared.parachute import run_agent  # noqa: E402


def call_api(prompt, options, context):
    """Ejecuta el agente centralizado con el prompt de Promptfoo."""
    respuesta = run_agent(supervisor, prompt)
    return {"output": respuesta}

