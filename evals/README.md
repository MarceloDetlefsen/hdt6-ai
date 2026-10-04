# Hoja de Trabajo 6 - Evals

Evaluación del sistema de agentes desarrollado para Parachute S.A. utilizando
[Promptfoo](https://www.promptfoo.dev/).

## Objetivo

El sistema desarrollado para Parachute S.A. tiene dos funcionalidades
principales:

1. Resolver preguntas frecuentes.
2. Agendar citas tomando en cuenta las condiciones meteorológicas.

Para evaluar ambas funcionalidades se implementaron evaluaciones con Promptfoo
que cubren los cuatro criterios solicitados:

- factuality;
- evaluaciones determinísticas (`icontains` y `regex`);
- latencia;
- tool execution.

La estrategia separa las evaluaciones determinísticas de las evaluaciones que
requieren un LLM como juez. Esto permite obtener resultados reproducibles sin
que las restricciones del proveedor LLM afecten innecesariamente toda la suite.

---

# Estructura de los evals

Los archivos principales se encuentran organizados de la siguiente manera:

```text
hdt6-ai/
├── README.md
├── assertions.js
├── assertions.test.js
├── reporte-faq.json
├── reporte-p3.json
├── reporte-factuality.json
│
└── evals/
    ├── provider.py
    ├── provider_p3.py
    ├── promptfooconfig.yaml
    ├── promptfooconfig-faq.yaml
    ├── promptfooconfig-p3.yaml
    ├── promptfooconfig-factuality.yaml
    │
    └── cases/
        ├── faq.yaml
        └── appointments.yaml
```

Las tres suites utilizadas como evidencia principal son:

| Suite | Casos | Objetivo |
| --- | ---: | --- |
| FAQ | 6 | FAQ, determinísticos, latencia y tools |
| P3 | 15 | Citas, reglas de negocio, latencia, tools y persistencia |
| Factuality | 2 | Factuality mediante LLM judge para FAQ y citas |

`promptfooconfig.yaml` se conserva como configuración end-to-end conjunta para
ejecutar todos los casos cuando se desea analizar el sistema completo.

---

# Instalación y preparación

Desde la raíz del repositorio:

```bash
npm install
```

Activar el ambiente virtual utilizado por el proyecto:

```bash
source ../ai-function-calls/.venv/bin/activate
```

Cargar las variables de ambiente:

```bash
set -a
source .env
set +a
```

Las credenciales y archivos `.env` no deben incluirse en el repositorio.

---

# 1. Evaluación de preguntas frecuentes (FAQ)

Los casos de FAQ están definidos en:

```text
evals/cases/faq.yaml
```

y se ejecutan utilizando:

```text
evals/promptfooconfig-faq.yaml
```

La suite contiene seis casos.

Se evalúan preguntas cuya respuesta existe en la base de conocimientos y
preguntas para las cuales el agente debe reconocer que no posee información
suficiente.

## Evaluaciones determinísticas

Para información concreta se utilizan assertions como `icontains` y `regex`.

Por ejemplo, para la edad mínima:

```yaml
- type: icontains
  value: "18 años cumplidos"
```

Para el peso máximo se utiliza un regex tolerante a diferentes caracteres
Unicode utilizados como espacio:

```yaml
- type: regex
  value: '100[\s\u00A0\u202F]*kg'
```

Esto evita un falso negativo cuando el modelo devuelve visualmente `100 kg`
pero utiliza un espacio Unicode en lugar de un espacio ASCII convencional.

## Tool execution de FAQ

Los casos también especifican las herramientas que deben ejecutarse.

Por ejemplo:

```yaml
required_tools:
  - name: "consultar_faq"
    origin: "agent:SupervisorCentral"

  - name: "search_knowledge_base"
    origin: "agent:FAQWorker"
    error: false
```

La assertion:

```yaml
- type: javascript
  value: file://${configDir}/../assertions.js:toolCallsAndAppointments
```

comprueba la evidencia real registrada por el provider.

Por lo tanto, no basta con que la respuesta textual sea correcta. También debe
haberse utilizado la ruta esperada de herramientas.

## Ejecutar FAQ

```bash
PROMPTFOO_CONFIG_DIR="$PWD/.promptfoo" \
npx --no-install promptfoo eval \
  -c evals/promptfooconfig-faq.yaml \
  --no-cache \
  -o reporte-faq.json
```

El reporte resultante se guarda en:

```text
reporte-faq.json
```

---

# 2. Evaluación de calendarización de citas

Los casos de calendarización se encuentran en:

```text
evals/cases/appointments.yaml
```

Se utiliza una suite aislada:

```text
evals/promptfooconfig-p3.yaml
```

junto con:

```text
evals/provider_p3.py
```

La suite contiene 15 casos que cubren escenarios como:

- clima IDEAL;
- clima MARGINAL;
- límite inferior de viento marginal;
- límite superior de viento marginal;
- cobertura nubosa marginal;
- viento superior al límite;
- ráfagas superiores al límite;
- precipitación;
- cobertura nubosa superior al límite;
- fecha actual;
- fecha pasada;
- fecha fuera de la ventana meteorológica;
- fecha inválida;
- fallo simulado de la API meteorológica.

---

# Provider P3 determinista

`provider_p3.py` utiliza los wrappers y herramientas de la arquitectura
centralizada, pero no depende de que un LLM decida emitir cada tool call.

Esto permite evaluar las reglas de negocio de manera reproducible.

Los datos externos variables, como el clima y la fecha actual, se controlan
mediante fixtures.

Esto no reemplaza las herramientas. Las reglas reales de validación,
clasificación meteorológica y calendarización continúan ejecutándose.

---

# Dependencias aisladas

Los casos pueden definir:

| Variable | Uso |
| --- | --- |
| `fixed_today` | Fecha controlada para validaciones. |
| `weather_fixture` | Condiciones meteorológicas simuladas. |
| `weather_sequence` | Secuencia de respuestas meteorológicas. |
| `initial_appointments` | Estado inicial de citas. |
| `required_tools` | Herramientas que deben ejecutarse. |
| `forbidden_tools` | Herramientas que no deben ejecutarse. |
| `expected_created_appointments` | Número esperado de citas creadas. |

Cada caso utiliza almacenamiento temporal.

Los evals no deben modificar las citas reales de la aplicación.

---

# Tool execution y persistencia

Además de comprobar las herramientas ejecutadas, los evals verifican los
efectos producidos por ellas.

El provider devuelve metadata con una estructura similar a:

```json
{
  "tool_calls": [],
  "appointments": {
    "initial": [],
    "final": [],
    "created": []
  }
}
```

Esto permite distinguir entre:

```text
"el agente dijo que creó una cita"
```

y:

```text
"la herramienta realmente creó una cita"
```

Por ejemplo:

```yaml
expected_created_appointments: 1
```

exige que aparezca una cita nueva en `metadata.appointments.created`.

En escenarios inseguros se utiliza:

```yaml
expected_created_appointments: 0
```

junto con herramientas prohibidas como:

```yaml
forbidden_tools:
  - name: "calendarizar_cita"
  - name: "schedule_tool"
```

---

# Evaluaciones determinísticas de citas

Los casos utilizan expresiones regulares.

Ejemplo de una condición insegura:

```yaml
- type: regex
  value: '(NO SEGURO|PROHIBIDO|no fue calendarizada)'
```

Estas assertions comprueban el contenido de la respuesta, mientras que
`toolCallsAndAppointments` comprueba el comportamiento interno.

---

# Latencia

Tanto FAQ como P3 incluyen una assertion de latencia:

```yaml
- type: latency
  threshold: 60000
```

El umbral utilizado es de 60 segundos.

Es importante distinguir entre el timeout técnico y la evaluación de latencia.

El timeout determina cuánto tiempo puede permanecer ejecutándose un caso antes
de ser cancelado.

La assertion `latency`, en cambio, representa el criterio evaluado. Un caso que
tarde más de 60 segundos puede considerarse incorrecto respecto a latencia
aunque técnicamente haya logrado finalizar.

Para evitar mediciones artificialmente bajas por caché, las evaluaciones de
latencia se ejecutan utilizando:

```bash
--no-cache
```

---

# Ejecutar P3

```bash
PROMPTFOO_CONFIG_DIR="$PWD/.promptfoo" \
npx --no-install promptfoo eval \
  -c evals/promptfooconfig-p3.yaml \
  --no-cache \
  -o reporte-p3.json
```

## Resultado obtenido

La ejecución final de P3 produjo:

```text
15 passed
0 failed
0 errors
```

Los 15 casos finalizaron correctamente.

---

# 3. Factuality

Además de las assertions determinísticas, la hoja solicita una evaluación de
factuality.

Para esto se utiliza el grader nativo de Promptfoo:

```yaml
- type: factuality
  value: "{{reference}}"
  provider: groq:openai/gpt-oss-20b
  metric: Factuality
```

La respuesta generada por el agente se compara contra una referencia definida
previamente en cada caso:

```yaml
reference: "..."
```

La referencia no se genera a partir de la respuesta evaluada.

---

# ¿Por qué factuality se ejecuta por separado?

Inicialmente se intentó aplicar el grader de factuality globalmente sobre los
21 casos.

Esta configuración implica que cada caso no solo ejecuta el sistema multiagente,
sino que además necesita otra inferencia para que el LLM judge evalúe la
respuesta.

Durante las pruebas se observó que esto incrementaba considerablemente:

- la cantidad de llamadas remotas;
- los tokens consumidos;
- la latencia total;
- la probabilidad de alcanzar los límites del proveedor;
- los timeouts de la evaluación completa.

Por esta razón se separó factuality de las suites determinísticas.

Esta separación no elimina factuality.

En su lugar, factuality se evalúa explícitamente sobre una muestra
representativa de las dos funcionalidades del sistema:

1. una pregunta FAQ;
2. una calendarización de cita.

De esta manera se demuestra el uso del grader solicitado sin convertir las
limitaciones externas del proveedor en errores de los 21 casos determinísticos.

---

# Ejecutar factuality

```bash
PROMPTFOO_CONFIG_DIR="$PWD/.promptfoo" \
npx --no-install promptfoo eval \
  -c evals/promptfooconfig-factuality.yaml \
  --no-cache \
  -o reporte-factuality.json
```

## Resultado obtenido

La ejecución final produjo:

```text
2 passed
0 failed
0 errors
```

La ejecución utilizó un LLM judge y registró tokens específicamente asociados
al grading, confirmando que el grader de factuality fue ejecutado.

---

# Evidencia de ejecución de herramientas

`evals/provider.py` crea una traza independiente para cada caso.

La respuesta del agente permanece en:

```text
output
```

mientras que la evidencia de herramientas se devuelve en:

```json
{
  "metadata": {
    "tool_calls": [
      {
        "order": 1,
        "name": "consultar_faq",
        "arguments": {},
        "result": "...",
        "error": null,
        "origin": "agent:SupervisorCentral"
      }
    ]
  }
}
```

La evaluación registra llamadas observables realmente ejecutadas.

No se infiere la ejecución de una herramienta a partir del texto de la
respuesta.

Esto permite comprobar:

- qué herramienta fue llamada;
- desde qué agente;
- en qué orden;
- con qué argumentos;
- si produjo un error;
- qué resultado produjo.

---

# Interpretación de resultados

## PASS

Todas las assertions del caso se cumplieron.

## FAIL

La ejecución terminó, pero una o más assertions no cumplieron el criterio.

Por ejemplo:

- contenido incorrecto;
- factuality incorrecto;
- herramienta requerida ausente;
- herramienta prohibida ejecutada;
- persistencia incorrecta;
- latencia superior al umbral.

## ERROR

El caso no pudo completar normalmente la evaluación.

Ejemplos observados durante desarrollo:

- timeout;
- rate limit del proveedor;
- límite global de duración.

Los errores de infraestructura se distinguen de los fallos funcionales del
agente.

---

# Reportes finales

Los reportes principales generados por Promptfoo son:

```text
reporte-faq.json
reporte-p3.json
reporte-factuality.json
```

También se pueden inspeccionar los resultados utilizando:

```bash
npx --no-install promptfoo view
```

---

# Cobertura de requisitos

| Requisito | Evidencia |
| --- | --- |
| FAQ | `faq.yaml` + `reporte-faq.json` |
| Calendarización | `appointments.yaml` + `reporte-p3.json` |
| Factuality | `promptfooconfig-factuality.yaml` + `reporte-factuality.json` |
| Determinísticos | `icontains` / `regex` |
| Latencia | assertion `latency` |
| Tool execution | `assertions.js` + `metadata.tool_calls` |
| Persistencia | `metadata.appointments.created` |

---

# Resumen de la estrategia

La evaluación se divide en tres suites:

```text
FAQ
 ├── 6 casos
 ├── determinísticos
 ├── latencia
 └── tool execution

P3 / citas
 ├── 15 casos
 ├── determinísticos
 ├── latencia
 ├── tool execution
 └── persistencia

Factuality
 ├── 1 caso FAQ
 ├── 1 caso de cita
 └── LLM judge de Promptfoo
```

Esta separación permite evaluar cada propiedad con la técnica apropiada y evita
confundir fallos funcionales del agente con restricciones de infraestructura
del proveedor LLM.
