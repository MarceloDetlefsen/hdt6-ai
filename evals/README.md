# Evidencia de ejecución de herramientas

`evals/provider.py` crea un `ToolCallTrace` nuevo para cada caso de Promptfoo y
lo activa durante toda la ejecución de `run_agent`. La respuesta final continúa
siendo texto en `output`; la evidencia se devuelve en:

```json
{
  "metadata": {
    "tool_calls": [
      {
        "order": 1,
        "name": "consultar_faq",
        "arguments": {"input": "..."},
        "result": "...",
        "error": null,
        "origin": "agent:SupervisorCentral"
      }
    ]
  }
}
```

Se registran las llamadas observables realmente ejecutadas:

- Delegaciones del supervisor a workers (`consultar_faq`, `consultar_clima` y
  `calendarizar_cita`), mediante los hooks del Agents SDK.
- Herramientas locales de los workers, mediante los mismos hooks.
- Búsqueda efectiva de HDT4 (`search_knowledge_base`), en
  `hdt4/src/tools.py`.
- Llamadas directas de los guards, con origen `guard:calendar` o
  `guard:domain`.

El orden se asigna al momento de iniciar cada llamada. Si una excepción impide
que el SDK emita el callback de finalización, la llamada queda registrada con
`result: null` y el error capturado por `run_agent`.

No se infieren llamadas a partir del texto de la respuesta. Tampoco se registran
como herramientas del agente las llamadas HTTP internas de Open-Meteo, las
consultas SQL/embeddings internas de PostgreSQL ni las solicitudes HTTP al
proveedor LLM; la herramienta que las encapsula sí queda registrada cuando fue
ejecutada.

El registro se crea dentro de `call_api`, por lo que cada caso empieza con una
lista vacía y su primer evento tiene `order: 1`.

## Dependencias aisladas por caso

El proveedor acepta variables opcionales en cada caso de Promptfoo:

- `fixed_today`: fecha `YYYY-MM-DD` que usa la validación real de fechas.
- `weather_fixture`: objeto JSON con `temperature_c`, `precipitation_mm`,
  `cloud_cover_pct`, `visibility_m`, `wind_speed_kmh` y `wind_gust_kmh`.
- `weather_sequence`: lista JSON de fixtures consumidos en orden por cada
  consulta meteorológica. Esto permite simular un cambio entre la consulta de
  clima y la reserva.
- `initial_appointments`: lista JSON con las citas iniciales del caso.

Las reglas de `validate_date`, `evaluate_weather` y `schedule_tool` permanecen
activas. Cuando se proporciona un fixture, únicamente se sustituye la fuente de
datos de `fetch_weather`; no se sustituye el LLM ni las herramientas.

Cada caso escribe las citas en un archivo temporal y devuelve el estado en
`metadata.appointments`:

```json
{
  "initial": [],
  "final": [],
  "created": []
}
```

El archivo temporal, la ruta `APPOINTMENTS_PATH`, la fecha fija y los fixtures
se restauran al terminar el caso, incluso si ocurre un error. Los evals nunca
escriben en `data/citas.json`.
