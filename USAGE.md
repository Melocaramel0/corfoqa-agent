# Guía de Uso

## Ejecución desde Línea de Comandos

### Validación Completa

Ejecuta todos los modos en secuencia (Explorer → Extractor → Completer → Validator → Matcher → Reporter):

```bash
python main.py --mode full --form-url https://formulario.com --no-headless
```

### Solo Exploración

Descubre la estructura del formulario sin completarlo:

```bash
python main.py --mode explore --form-url https://formulario.com --no-headless
```

### Solo Extracción

Extrae todos los campos y sus metadatos:

```bash
python main.py --mode extract --form-url https://formulario.com
```

### Autocompletado

Extrae y completa el formulario con datos de prueba:

```bash
python main.py --mode complete --form-url https://formulario.com --no-headless
```

### Validación de Obligatoriedad

Detecta qué campos son obligatorios:

```bash
python main.py --mode validate --form-url https://formulario.com --evidence
```

### Matching QA

Compara el formulario contra la lista de campos fundamentales:

```bash
python main.py --mode match --form-url https://formulario.com --qa-fields test_data/campos_corfo.txt
```

## Opciones de Línea de Comandos

### Obligatorias

- `--form-url URL`: URL del formulario objetivo (obligatoria si no está en .env)

### Opcionales

- `--mode MODE`: Modo de operación (explore, extract, complete, validate, match, full). Por defecto: `full`
- `--login-url URL`: URL de login si el formulario requiere autenticación
- `--qa-fields PATH`: Ruta al archivo de campos QA. Por defecto: `test_data/campos_corfo.txt`
- `--no-headless`: Ejecutar navegador en modo visible (útil para debugging)
- `--evidence`: Capturar screenshots como evidencia

## Uso Programático

### Ejemplo Básico

```python
import asyncio
from config import Config
from main import FormValidationAgent

async def validar_formulario():
    config = Config(
        form_url="https://formulario.com",
        mode="full",
        headless=False,
        evidence_enabled=True
    )
    
    agent = FormValidationAgent(config)
    results = await agent.run()
    
    return results

# Ejecutar
asyncio.run(validar_formulario())
```

### Ejemplo Avanzado: Solo Campos Faltantes

```python
import asyncio
from config import Config
from main import FormValidationAgent

async def buscar_campos_faltantes():
    config = Config(
        form_url="https://formulario.com",
        mode="match",
        headless=True,
        qa_fields_path="mis_campos.txt"
    )
    
    agent = FormValidationAgent(config)
    results = await agent.run()
    
    # Extraer campos faltantes
    if "matcher" in results:
        match_results = results["matcher"]["match_results"]
        faltantes = [
            r["qa_field"] for r in match_results 
            if r["status"] == "FALTANTE"
        ]
        
        print(f"Campos QA faltantes: {len(faltantes)}")
        for campo in faltantes:
            print(f"  - {campo}")
    
    return faltantes

asyncio.run(buscar_campos_faltantes())
```

## Resultados y Salidas

### Estructura de Directorios de Salida

```
outputs/
├── json/                    # Informes JSON estructurados
│   └── report_YYYYMMDD_HHMMSS.json
├── reports/                 # Informes legibles en Markdown
│   └── report_YYYYMMDD_HHMMSS.md
└── evidence/                # Screenshots de evidencia
    ├── before_validation.png
    └── after_validation_attempt.png
```

### Informe JSON

Contiene todos los datos estructurados:

```json
{
  "metadata": {
    "generated_at": "2024-10-07T20:30:00",
    "form_url": "https://...",
    "execution_time_seconds": 45.2
  },
  "explorer": { ... },
  "extractor": {
    "fields": [
      {
        "canonical_key": "rut",
        "type": "text",
        "required_flag": true,
        "label_visible": "RUT"
      }
    ]
  },
  "validator": {
    "required_fields": ["rut", "nombre", "email"],
    "optional_fields": ["telefono"]
  },
  "matcher": {
    "match_results": [
      {
        "qa_field": "RUT",
        "status": "PRESENTE",
        "found_field": "rut",
        "similarity": 1.0
      }
    ],
    "statistics": {
      "coverage_percentage": 85.5
    }
  },
  "anomalies": [
    {
      "title": "Campos QA Faltantes",
      "severity": "HIGH",
      "fields": ["campo_faltante"]
    }
  ]
}
```

### Informe Markdown

Informe legible para humanos con:
- Resumen ejecutivo
- Pasos del formulario
- Campos obligatorios/opcionales
- Matching QA con campos faltantes
- Anomalías detectadas
- Métricas de ejecución

## Casos de Uso

### 1. Auditoría de Formulario Nuevo

```bash
# Primer paso: Explorar estructura
python main.py --mode explore --form-url URL --no-headless

# Segundo paso: Validar contra QA
python main.py --mode match --form-url URL --qa-fields campos_requeridos.txt
```

### 2. Validación Continua (CI/CD)

```bash
# Ejecución headless con evidencia
python main.py --mode full --form-url URL --evidence

# Verificar código de salida
if [ $? -ne 0 ]; then
  echo "Validación falló"
  exit 1
fi
```

### 3. Debugging de Campo Específico

```bash
# Ver navegador y evidencia
python main.py --mode validate --form-url URL --no-headless --evidence

# Revisar screenshots en outputs/evidence/
```

### 4. Comparación Entre Versiones

```bash
# Versión anterior
python main.py --mode extract --form-url URL_V1
mv outputs/json/report_*.json report_v1.json

# Versión nueva
python main.py --mode extract --form-url URL_V2
mv outputs/json/report_*.json report_v2.json

# Comparar manualmente los JSON
```

## Personalización

### Campos QA Personalizados

Crea tu propio archivo de campos:

```txt
# mis_campos.txt
RUT Empresa
Razón Social
Email Contacto
Teléfono
Proyecto
Monto
```

Úsalo:

```bash
python main.py --mode match --form-url URL --qa-fields mis_campos.txt
```

### Datos de Prueba Personalizados

Edita `data_generator.py` para ajustar los datos generados según tus necesidades.

## Tips y Mejores Prácticas

### 1. Siempre Empieza con Exploración

Antes de validaciones complejas, explora el formulario:

```bash
python main.py --mode explore --form-url URL --no-headless
```

### 2. Usa Evidencia en Producción

Siempre captura screenshots para debugging posterior:

```bash
python main.py --mode full --form-url URL --evidence
```

### 3. Headless para CI/CD, Visible para Debugging

- Desarrollo: `--no-headless`
- CI/CD: `--headless` (por defecto)

### 4. Revisa los Logs

El archivo `agent.log` contiene información detallada:

```bash
tail -f agent.log
```

### 5. Ejecuta Incrementalmente

No es necesario ejecutar siempre el modo `full`. Ejecuta solo lo que necesitas:

- ¿Cambió la estructura? → `explore`
- ¿Nuevos campos? → `extract`
- ¿Revisar obligatoriedad? → `validate`
- ¿Verificar especificación? → `match`

## Solución de Problemas Comunes

### El agente no encuentra campos

- Usa `--no-headless` para ver qué está pasando
- Verifica que el formulario cargue completamente
- Aumenta timeouts en `config.py`

### Campos no se completan

- Revisa `data_generator.py` para tu caso de uso
- Verifica que los tipos de campo sean reconocidos
- Chequea validaciones del formulario que puedan bloquear

### Matching QA no encuentra campos

- Normaliza los nombres en `campos_corfo.txt`
- Ajusta `qa_match_threshold` en `config.py`
- Revisa sinónimos en `utils/normalizer.py`

### El navegador no se cierra

- Usa Ctrl+C para terminar
- Verifica que Playwright esté instalado correctamente
- Reinicia tu terminal

## Integración con CI/CD

### GitHub Actions

```yaml
- name: Validar Formulario
  run: |
    pip install -r requirements.txt
    playwright install chromium
    python main.py --mode full --form-url $FORM_URL
```

### GitLab CI

```yaml
validate_form:
  script:
    - pip install -r requirements.txt
    - playwright install chromium
    - python main.py --mode full --form-url $FORM_URL
  artifacts:
    paths:
      - outputs/
```

