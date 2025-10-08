# Arquitectura del Agente de Validación de Formularios

## Visión General

El Agente de Validación de Formularios es un sistema modular diseñado para automatizar la validación, extracción y análisis de formularios web complejos y multi-paso. Utiliza Crawlee-Python y Playwright para navegación robusta.

## Principios de Diseño

### 1. Modularidad
Cada modo de operación es independiente y puede ejecutarse por separado o en secuencia.

### 2. Resiliencia
Múltiples estrategias de selección, reintentos automáticos y detección de bucles para manejar formularios impredecibles.

### 3. Extensibilidad
Fácil agregar nuevos tipos de campos, validaciones y heurísticas sin modificar el núcleo.

### 4. Trazabilidad
Cada acción genera evidencia (logs, screenshots) para debugging y auditoría.

## Estructura de Módulos

```
crawlee-corfo/
├── main.py                 # Orquestador principal
├── config.py               # Configuración centralizada
├── data_generator.py       # Generador de datos de prueba
├── reporter.py             # Generación de informes
├── modes/                  # Modos de operación
│   ├── explorer.py         # Descubrimiento de estructura
│   ├── extractor.py        # Extracción de campos
│   ├── completer.py        # Autocompletado
│   ├── validator.py        # Validación de obligatoriedad
│   └── matcher.py          # Matching con QA
└── utils/                  # Utilidades compartidas
    ├── selectors.py        # Estrategias de selección
    ├── normalizer.py       # Normalización de texto
    └── resilience.py       # Manejo de errores
```

## Flujo de Ejecución

### Modo Full (Completo)

```
┌─────────────┐
│   INICIO    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   1. EXPLORER   │  ← Mapea estructura del formulario
│                 │    - Detecta pasos/secciones
│                 │    - Identifica botones de navegación
│                 │    - Descubre mecanismos de progreso
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. EXTRACTOR   │  ← Extrae todos los campos
│                 │    - Captura metadatos completos
│                 │    - Detecta tipos de campo
│                 │    - Obtiene labels y ayudas
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. COMPLETER   │  ← Autocompleta formulario
│                 │    - Genera datos coherentes por tipo
│                 │    - Sube archivos PDF
│                 │    - Maneja campos condicionales
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. VALIDATOR   │  ← Detecta obligatoriedad
│                 │    - Múltiples señales (HTML, ARIA, visual)
│                 │    - Pruebas de blur y submit
│                 │    - Captura mensajes de error
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   5. MATCHER    │  ← Compara con lista QA
│                 │    - Match exacto, sinónimos, similitud
│                 │    - Identifica faltantes
│                 │    - Detecta extras no especificados
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   6. REPORTER   │  ← Genera informes
│                 │    - JSON estructurado
│                 │    - Markdown legible
│                 │    - Evidencias (screenshots)
└────────┬────────┘
         │
         ▼
     ┌──────┐
     │  FIN │
     └──────┘
```

## Componentes Principales

### 1. Explorer (Explorador)

**Responsabilidad:** Descubrir y mapear la estructura del formulario.

**Estrategias:**
- Detección de tipo de estructura (wizard, tabs, single-page)
- Identificación de botones de navegación mediante múltiples selectores
- Mapeo incremental con detección de bucles
- Captura de títulos y URLs por paso

**Salida:**
```json
{
  "total_steps": 7,
  "steps": [
    {
      "index": 0,
      "title": "Datos Personales",
      "url": "https://..."
    }
  ],
  "navigation_buttons": {
    "next": ["button:has-text('Siguiente')"],
    "previous": ["button:has-text('Anterior')"],
    "submit": ["button:has-text('Enviar')"]
  }
}
```

### 2. Extractor (Extractor)

**Responsabilidad:** Extraer todos los campos con metadatos completos.

**Metadatos Capturados:**
- Identificación: id, name, type
- Etiquetas: label, placeholder, help_text
- ARIA: aria-label, aria-required, aria-invalid
- Validaciones: required, pattern, min/max, minLength/maxLength
- Opciones: para select, radio, checkbox
- Estado: visible, enabled, readonly
- Clave canónica para matching

**Estrategias:**
- Múltiples métodos para encontrar labels (for, ancestor, preceding-sibling)
- Detección automática de tipo de campo
- Extracción de opciones de selects y grupos radio/checkbox
- Generación de selectores robustos

**Salida:**
```json
{
  "total_fields": 45,
  "fields": [
    {
      "canonical_key": "rut",
      "type": "text",
      "label_visible": "RUT",
      "required_flag": true,
      "pattern": "^[0-9]+-[0-9Kk]$"
    }
  ]
}
```

### 3. Completer (Completador)

**Responsabilidad:** Autocompletar formulario con datos de prueba coherentes.

**Tipos de Datos Soportados:**
- RUT/RUN chileno (con dígito verificador válido)
- Nombres y apellidos
- Emails y teléfonos
- Fechas (nacimiento, inicio actividades, etc.)
- Montos (CLP, UF, USD)
- Direcciones chilenas (región, comuna)
- Razones sociales y giros
- Uploads de archivos PDF

**Características:**
- Coherencia entre campos relacionados (mismo nombre en varios lugares)
- Respeto a restricciones (min/max, pattern, accept)
- Generación determinística (seed=42 para reproducibilidad)
- Manejo de campos condicionales

**Salida:**
```json
{
  "completion_rate": 95.5,
  "completed_fields": 43,
  "failed_fields": 2
}
```

### 4. Validator (Validador)

**Responsabilidad:** Detectar obligatoriedad mediante múltiples señales.

**Señales de Obligatoriedad:**
1. Atributo HTML `required`
2. Atributo ARIA `aria-required="true"`
3. Asterisco (*) en label
4. Palabras clave ("obligatorio", "requerido")
5. Validaciones restrictivas (pattern, minLength)
6. Test de blur (aparece error al dejar campo vacío)
7. Test de submit (bloquea al intentar avanzar)

**Lógica de Decisión:**
- ≥2 señales positivas → Obligatorio
- 1 señal → Incierto (requiere revisión)
- 0 señales → Opcional

**Salida:**
```json
{
  "required_fields": ["rut", "nombre", "email"],
  "optional_fields": ["telefono_secundario"],
  "uncertain_fields": ["comentarios"],
  "validation_events": [
    {
      "field_key": "email",
      "event_type": "validation_error",
      "message": "Email es obligatorio"
    }
  ]
}
```

### 5. Matcher (Comparador QA)

**Responsabilidad:** Comparar campos encontrados contra lista de Campos Fundamentales.

**Estrategias de Matching:**
1. **Exact Match:** Claves canónicas idénticas (similitud = 1.0)
2. **Synonym Match:** Sinónimos conocidos (similitud = 0.95)
3. **Similarity Match:** Similitud de texto combinada:
   - Jaccard (palabras comunes): 60%
   - Fuzzy string matching: 40%

**Estados Posibles:**
- **PRESENTE:** Campo QA encontrado (similitud ≥ 0.9)
- **POTENCIAL_EQUIVALENTE:** Posible match (0.7 ≤ similitud < 0.9)
- **FALTANTE:** Campo QA no encontrado
- **EXTRA_NO_QA:** Campo en formulario pero no en lista QA

**Salida:**
```json
{
  "statistics": {
    "coverage_percentage": 85.5,
    "present": 47,
    "missing": 8,
    "potential_equivalent": 3
  },
  "match_results": [
    {
      "qa_field": "RUT",
      "status": "PRESENTE",
      "found_field": "rut",
      "similarity": 1.0,
      "match_type": "exact"
    }
  ]
}
```

### 6. Reporter (Reportero)

**Responsabilidad:** Generar informes completos con evidencias.

**Formatos de Salida:**
1. **JSON estructurado:** Para procesamiento automático
2. **Markdown legible:** Para revisión humana
3. **Screenshots:** Evidencia visual

**Secciones del Informe:**
- Resumen ejecutivo con métricas clave
- Estructura del formulario (pasos)
- Campos obligatorios/opcionales
- Matching QA (presentes, faltantes, equivalentes)
- Anomalías detectadas con severidad
- Propuestas de mejora
- Métricas de ejecución

**Detección de Anomalías:**
- Campos QA faltantes (HIGH)
- Campos presentes pero no obligatorios (MEDIUM)
- Baja tasa de autocompletado (MEDIUM)
- Campos con tipo desconocido (LOW)
- Errores de validación inesperados (MEDIUM)

## Utilidades

### utils/selectors.py

**SelectorStrategy:** Localización robusta de elementos mediante múltiples estrategias.

**Métodos:**
- `find_element()`: Intenta múltiples selectores
- `find_by_text()`: Busca por texto visible
- `find_by_label()`: Busca campo asociado a label
- `safe_click()`: Click con reintentos y scroll
- `safe_fill()`: Relleno seguro con limpieza previa

### utils/normalizer.py

**Funciones de Normalización:**
- `normalize_text()`: lowercase, sin tildes, sin stopwords
- `get_canonical_key()`: Clave normalizada con expansión de abreviaturas
- `calculate_similarity()`: Similitud Jaccard entre textos
- `find_synonyms()`: Busca sinónimos conocidos

**Diccionario de Sinónimos:**
```python
{
  "nombre": ["nombres", "primer nombre"],
  "rut": ["run", "rol unico tributario"],
  "email": ["correo", "correo electronico"]
}
```

### utils/resilience.py

**RetryStrategy:** Reintentos con backoff exponencial.

**LoopDetector:** Detecta bucles infinitos en navegación.

**NavigationWaiter:** Esperas inteligentes:
- `wait_for_navigation_complete()`: networkidle o load
- `wait_for_element_stable()`: elemento visible y estable
- `wait_for_any_element()`: primer elemento que aparezca
- `wait_for_spinner_gone()`: espera a que desaparezcan loaders

## Configuración

### config.py

**Config (Pydantic Model):**
- URLs y credenciales
- Modo de operación
- Configuración del navegador
- Timeouts y reintentos
- Rutas de archivos
- Flags de evidencia

**Carga desde:**
- Variables de entorno (.env)
- Argumentos de línea de comandos
- Valores por defecto

## Data Generator

### data_generator.py

**DataGenerator:** Generador determinístico de datos de prueba.

**Métodos Principales:**
- `generate_rut()`: RUT válido con DV correcto
- `generate_nombre_completo()`: Nombre + apellidos
- `generate_email()`: Email con dominio de prueba
- `generate_telefono()`: Formato chileno (+56)
- `generate_fecha()`: Por tipo (nacimiento, inicio, etc.)
- `generate_monto()`: Con separador de miles
- `generate_direccion()`: Región y comuna válidas

**Coherencia:**
Cache interno para mantener consistencia (mismo nombre usado múltiples veces).

## Patrones de Diseño

### 1. Strategy Pattern
Múltiples estrategias de selección y matching que se intentan en secuencia.

### 2. Builder Pattern
Construcción incremental de objetos FormField con todos sus metadatos.

### 3. Observer Pattern
Logging detallado en cada paso para trazabilidad.

### 4. Template Method
Estructura común para todos los modos (execute → process → return results).

## Consideraciones de Seguridad

### 1. Datos de Prueba
- NUNCA usar credenciales reales
- Datos ficticios y coherentes
- Sin persistencia de información sensible

### 2. Ejecución Controlada
- No envíos reales (se detiene antes del submit final)
- Modo headless por defecto para servidores
- Evidencia con información no sensible

### 3. Validación de Entradas
- Pydantic para validación de configuración
- Sanitización de rutas de archivos
- Timeouts para prevenir ejecuciones infinitas

## Escalabilidad

### Ejecución en Paralelo
Crawlee maneja múltiples requests concurrentes. Posible extender para validar múltiples formularios simultáneamente.

### Storage
Salidas en disco con timestamp para mantener historial de ejecuciones.

### Métricas
Todas las operaciones registran tiempo de ejecución para identificar cuellos de botella.

## Limitaciones Conocidas

1. **Login automático no implementado:** Requiere customización por sitio
2. **Captchas:** No soportados (requieren intervención manual)
3. **JavaScript complejo:** Formularios con validaciones muy dinámicas pueden requerir ajustes
4. **Idioma:** Optimizado para español (Chile), keywords y sinónimos en español

## Futuras Mejoras

1. **Login genérico:** Detectar tipos comunes de login y automatizar
2. **ML para similitud:** Usar embeddings para matching más inteligente
3. **Reglas de negocio:** Validar coherencia entre campos (fechas, montos)
4. **API REST:** Exponer funcionalidad como servicio
5. **Dashboard:** UI web para ver resultados en tiempo real
6. **Soporte multiidioma:** Keywords y sinónimos en inglés y otros idiomas

## Conclusión

El agente está diseñado para ser robusto, extensible y mantenible. Cada componente tiene una responsabilidad clara y puede evolucionar independientemente. La arquitectura modular permite agregar nuevas capacidades sin afectar el núcleo existente.

