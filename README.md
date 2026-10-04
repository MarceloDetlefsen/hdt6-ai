# Hoja de Trabajo 6 - Evals con Promptfoo

Sistema de asistencia conversacional para **Parachute S.A.** evaluado mediante
[Promptfoo](https://www.promptfoo.dev/).

El sistema fue desarrollado previamente utilizando tres patrones de
orquestación multiagente: Centralizada, Jerárquica y Descentralizada. Para esta
hoja de trabajo se seleccionó la arquitectura **Centralizada**, ya que fue la
arquitectura considerada más adecuada para continuar el desarrollo y realizar
los evals.

---

## 1. Objetivo

El agente de Parachute S.A. posee dos funcionalidades principales:

1. Resolver preguntas frecuentes utilizando la base de conocimientos de la
   empresa.
2. Calendarizar citas para paracaidismo considerando las condiciones
   meteorológicas y las reglas de seguridad.

El objetivo de esta hoja es evaluar ambas funcionalidades utilizando Promptfoo.

Los evals implementados cubren los cuatro criterios solicitados:

- **Factuality**
- **Evaluaciones determinísticas (`icontains` / `regex`)**
- **Latencia**
- **Tool execution**

Además, para las citas se comprueba el efecto real de las herramientas mediante
la persistencia o ausencia de nuevas citas.

---

## 2. Arquitectura evaluada

La arquitectura utilizada para HDT6 es la **Centralizada**.

El supervisor central coordina workers especializados para:

- consultas FAQ;
- consulta meteorológica;
- calendarización de citas.

Las reglas determinísticas compartidas, como validación de fechas, clasificación
meteorológica, búsqueda de FAQs y persistencia de citas, se encuentran
encapsuladas en la capa compartida del proyecto.

Los evals no se limitan a revisar el texto final del agente. También capturan
la traza de herramientas ejecutadas para verificar el comportamiento interno
del sistema.

---

## 3. Estrategia de evaluación

Los evals se dividen en dos suites principales.

### Suite principal

La configuración:

```text
evals/promptfooconfig.yaml
```

ejecuta **21 casos**:

```text
6 casos FAQ
15 casos de calendarización
----------------------------
21 casos totales
```

Esta suite evalúa:

- contenido determinístico;
- latencia;
- tool execution;
- herramientas prohibidas;
- persistencia de citas.

### Suite de factuality

La configuración:

```text
evals/promptfooconfig-factuality.yaml
```

utiliza el grader `factuality` de Promptfoo sobre una muestra representativa de
las dos funcionalidades:

```text
1 caso FAQ
1 caso de calendarización
```

Esta separación se explica más adelante.

---

## 4. Estructura de los evals

```text
evals/
├── promptfooconfig.yaml
├── promptfooconfig-factuality.yaml
├── provider_combined.py
├── provider.py
├── provider_p3.py
└── cases/
    ├── faq.yaml
    └── appointments.yaml

assertions.js
assertions.test.js

reporte-evals.json
reporte-factuality.json
```

### Providers

`provider_combined.py` funciona como punto de entrada de la suite principal.

Los casos se enrutan de la siguiente manera:

```text
provider_combined.py
        |
        +---- FAQ ------> provider.py
        |
        +---- Citas ----> provider_p3.py
```

Los casos FAQ utilizan el agente centralizado real.

Los casos de citas utilizan un provider determinista que conserva las reglas y
herramientas de la arquitectura, pero evita depender de que un LLM decida
emitir cada tool call durante escenarios meteorológicos controlados.

Esto permite evaluar las reglas de seguridad de manera reproducible.

---

## 5. Casos FAQ

Los casos FAQ se encuentran en:

```text
evals/cases/faq.yaml
```

Se incluyen seis escenarios:

- peso máximo permitido;
- edad mínima;
- ingreso de alimentos y bebidas;
- parqueo;
- pregunta sobre fútbol fuera del dominio;
- pregunta sobre KPOP fuera del dominio.

### Evaluaciones determinísticas

Se utilizan assertions como `icontains` y `regex`.

Por ejemplo:

```yaml
- type: icontains
  value: "18 años cumplidos"
```

Para el peso se utiliza:

```yaml
- type: regex
  value: '100[\s\u00A0\u202F]*kg'
```

Este regex permite diferentes caracteres Unicode utilizados como espacio entre
`100` y `kg`, evitando falsos negativos por diferencias de formato que no
cambian el significado de la respuesta.

---

## 6. Casos de calendarización

Los casos se encuentran en:

```text
evals/cases/appointments.yaml
```

La suite contiene 15 escenarios que cubren condiciones normales, límites y
errores.

Entre ellos:

- clima IDEAL;
- clima MARGINAL;
- límite de viento;
- límite de ráfagas;
- cobertura nubosa;
- precipitación;
- fecha actual;
- fecha pasada;
- fecha fuera de la ventana meteorológica;
- fecha inválida;
- fallo simulado del proveedor meteorológico.

Las condiciones meteorológicas se proporcionan mediante fixtures para que los
resultados sean reproducibles y no dependan del clima real del día en que se
ejecutan los evals.

---

## 7. Tool execution

Uno de los requisitos principales es comprobar que las herramientas correctas
sean llamadas.

No se infiere tool execution buscando nombres de herramientas dentro del texto
generado por el agente.

Los providers registran las llamadas reales y las exponen mediante metadata:

```json
{
  "metadata": {
    "tool_calls": [
      {
        "order": 1,
        "name": "consultar_faq",
        "arguments": {
          "input": "..."
        },
        "result": "...",
        "error": null,
        "origin": "agent:SupervisorCentral"
      }
    ]
  }
}
```

Los casos pueden definir herramientas obligatorias:

```yaml
required_tools:
  - name: "weather_tool"
    origin: "agent:WeatherWorker"
    error: false

  - name: "schedule_tool"
    origin: "agent:CalendarWorker"
    error: false
```

También pueden definir herramientas prohibidas:

```yaml
forbidden_tools:
  - name: "calendarizar_cita"
  - name: "schedule_tool"
```

La validación se realiza mediante:

```yaml
- type: javascript
  value: file://${configDir}/../assertions.js:toolCallsAndAppointments
```

De esta manera se comprueba:

- nombre de la herramienta;
- agente/origen;
- existencia de errores;
- herramientas requeridas;
- herramientas prohibidas;
- cantidad de citas creadas.

---

## 8. Persistencia de citas

Los evals de calendarización no consideran suficiente que el agente responda
textualmente que una cita fue creada.

También se inspecciona el estado persistido.

Los providers exponen:

```json
{
  "appointments": {
    "initial": [],
    "final": [],
    "created": []
  }
}
```

Los casos pueden especificar:

```yaml
expected_created_appointments: 1
```

cuando debe crearse una cita, o:

```yaml
expected_created_appointments: 0
```

cuando las condiciones impiden la calendarización.

Esto permite detectar una respuesta que diga que una cita fue agendada sin que
la herramienta haya producido realmente ese efecto.

---

## 9. Latencia

La suite principal utiliza la assertion de Promptfoo:

```yaml
- type: latency
  threshold: 60000
```

El criterio definido es de **60 segundos**.

El timeout técnico del provider es independiente del criterio de evaluación.

Esto significa que una ejecución puede disponer de un pequeño margen técnico
para finalizar, pero debe considerarse FAIL de latencia si supera los 60
segundos.

Las evaluaciones se ejecutan utilizando:

```text
--no-cache
```

para evitar que una respuesta almacenada reduzca artificialmente la latencia
observada.

---

## 10. Factuality

Para factuality se utiliza explícitamente el grader de Promptfoo:

```yaml
- type: factuality
  value: "{{reference}}"
  provider: groq:openai/gpt-oss-20b
  metric: Factuality
```

Cada caso proporciona una referencia factual previamente definida:

```yaml
reference: "..."
```

El grader compara la respuesta producida por el sistema contra esta referencia.

### ¿Por qué factuality se ejecuta por separado?

Inicialmente se probó ejecutar el grader de factuality sobre los 21 casos.

Sin embargo, cada evaluación de factuality necesita una inferencia adicional
del LLM judge, además de las llamadas realizadas por la propia arquitectura
multiagente.

Durante las pruebas esto produjo:

- mayor cantidad de llamadas remotas;
- mayor consumo de tokens;
- mayor latencia;
- presión sobre los límites del proveedor;
- timeouts durante la suite completa.

Se verificó de manera independiente que el grader de factuality funcionaba
correctamente.

Por ello se decidió separar las propiedades de evaluación:

```text
Suite principal
    |
    +-- determinísticos
    +-- latencia
    +-- tool execution
    +-- persistencia

Suite factuality
    |
    +-- FAQ representativo
    +-- cita representativa
    +-- LLM judge
```

La suite de factuality contiene un caso de cada funcionalidad, por lo que ambas
capacidades del sistema están representadas.

Esta separación evita confundir limitaciones del proveedor LLM con fallos
funcionales de las reglas de negocio.

---

## 11. Configuración del entorno

### Requisitos

- Python 3.10 o superior.
- Node.js y npm.
- Promptfoo.
- API key de Groq.
- Dependencias Python del proyecto.

Instalar las dependencias de Node:

```bash
npm install
```

Activar el entorno virtual correspondiente al proyecto:

```bash
source ../ai-function-calls/.venv/bin/activate
```

Cargar las variables:

```bash
set -a
source .env
set +a
```

La configuración utiliza, entre otras:

```dotenv
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

Las credenciales reales no deben incluirse en el repositorio.

---

## 12. Ejecutar los 21 casos principales

Desde la raíz del repositorio:

```bash
PROMPTFOO_CONFIG_DIR="$PWD/.promptfoo" \
npx --no-install promptfoo eval \
  -c evals/promptfooconfig.yaml \
  --no-cache \
  -o reporte-evals.json
```

La ejecución final obtuvo:

```text
20 passed (95.24%)
1 failed (4.76%)
0 errors
```

### Interpretación del único FAIL

El caso que no cumplió el criterio fue:

```text
¿Se permite el ingreso de alimentos y bebidas?
```

La traza demuestra que el sistema sí realizó la búsqueda FAQ y obtuvo la
información correspondiente.

Sin embargo, la ejecución completa excedió el criterio de latencia establecido.

El caso alcanzó el deadline técnico del provider antes de producir normalmente
la respuesta final.

Este resultado se conserva como FAIL deliberadamente.

No se aumentó el threshold de latencia únicamente para obtener un resultado de
100%, ya que la latencia es precisamente una de las propiedades que la hoja de
trabajo solicita evaluar.

Por lo tanto, este FAIL representa un hallazgo de la evaluación y no un error
de configuración de Promptfoo.

---

## 13. Ejecutar factuality

```bash
PROMPTFOO_CONFIG_DIR="$PWD/.promptfoo" \
npx --no-install promptfoo eval \
  -c evals/promptfooconfig-factuality.yaml \
  --no-cache \
  -o reporte-factuality.json
```

La ejecución validada durante el desarrollo obtuvo:

```text
2 passed
0 failed
0 errors
```

La corrida registró tokens correspondientes al proceso de grading, confirmando
que el LLM judge de factuality fue ejecutado.

---

## 14. Resultados

| Suite | Casos | PASS | FAIL | ERROR |
| --- | ---: | ---: | ---: | ---: |
| Principal: FAQ + citas | 21 | 20 | 1 | 0 |
| Factuality con LLM judge | 2 | 2 | 0 | 0 |

### Suite principal

```text
20 / 21 PASS
95.24%
0 errores
```

### Factuality

```text
2 / 2 PASS
100%
0 errores
```

---

## 15. Interpretación de resultados

### PASS

Todas las assertions aplicables al caso se cumplieron.

### FAIL

La ejecución terminó, pero al menos una propiedad evaluada no cumplió el
criterio.

Ejemplos:

- contenido incorrecto;
- latencia superior al threshold;
- herramienta requerida ausente;
- herramienta prohibida ejecutada;
- persistencia incorrecta;
- factuality insuficiente.

### ERROR

El eval no pudo ejecutarse normalmente por una condición técnica.

Por ejemplo:

- fallo de configuración;
- timeout externo;
- rate limit;
- error del provider.

Esta distinción permite evitar confundir un fallo funcional detectado por un
eval con un problema de infraestructura del sistema de evaluación.

---

## 16. Reportes

Los dos reportes principales entregados son:

```text
reporte-evals.json
reporte-factuality.json
```

`reporte-evals.json` contiene los 21 casos correspondientes a FAQ y
calendarización.

`reporte-factuality.json` contiene la evaluación mediante el grader LLM de
Promptfoo.

Los resultados también pueden visualizarse mediante:

```bash
npx --no-install promptfoo view
```

---

## 17. Cobertura de los requisitos

| Requisito | Implementación |
| --- | --- |
| FAQ | 6 casos en `evals/cases/faq.yaml` |
| Calendarización | 15 casos en `evals/cases/appointments.yaml` |
| Factuality | `promptfooconfig-factuality.yaml` |
| Determinísticos | `icontains` y `regex` |
| Latencia | assertion `latency` con threshold de 60 s |
| Tool execution | `assertions.js` + `metadata.tool_calls` |
| Herramientas requeridas | `required_tools` |
| Herramientas prohibidas | `forbidden_tools` |
| Persistencia | `expected_created_appointments` |
| Reporte Promptfoo | `reporte-evals.json` y `reporte-factuality.json` |

---

## 18. Resumen

La estrategia final utiliza dos niveles de evaluación:

```text
                 Parachute S.A.
                       |
              +--------+--------+
              |                 |
         Suite principal     Factuality
              |                 |
       21 casos totales      2 casos
              |                 |
        +-----+-----+        LLM judge
        |           |
      6 FAQ      15 citas
        |
        +-- contenido
        +-- latencia
        +-- tools

      citas
        |
        +-- contenido
        +-- latencia
        +-- tools
        +-- persistencia
```

Los resultados finales demuestran que las reglas de negocio, ejecución de
herramientas y factualidad pueden evaluarse independientemente, y que los evals
también permiten detectar problemas reales de calidad antes de desplegar el
sistema en producción.
