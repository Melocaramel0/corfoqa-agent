# Arquitectura del Sistema de Exploración Robusto

## 📋 Resumen

El sistema ha sido diseñado con **separación clara de responsabilidades** entre modos, permitiendo ejecución individual o en secuencia completa. El sistema se adapta dinámicamente a formularios con diferentes cantidades de pasos, preguntas y desplegables.

## 🔄 Flujo de Modos

### Modo Explorer
**Responsabilidad**: Mapear SOLO la estructura del formulario
- ✅ Detecta pasos dinámicamente desde la barra de navegación
- ✅ Identifica desplegables/acordeones (sin expandirlos)
- ✅ Prueba navegación entre pasos
- ✅ Retorna mapa estructural completo
- ❌ NO extrae valores de campos

**Salida**: Mapa JSON con:
```json
{
  "success": true,
  "total_steps": 7,
  "steps": [
    {
      "index": 0,
      "title": "Datos Generales Proyecto",
      "seccion_id": "1703864",
      "has_form_content": true,
      "total_collapsibles": 3,
      "collapsibles": [
        {
          "title": "Resumen estructura presupuestaria",
          "target_id": "subSeccion1703865_0_0",
          "selector": "a[data-toggle='collapse'][href='#subSeccion1703865_0_0']",
          "initially_collapsed": true
        }
      ]
    }
  ]
}
```

### Modo Extractor
**Responsabilidad**: Extraer CONTENIDO usando el mapa del Explorer
- ✅ Recibe mapa estructural del Explorer
- ✅ Navega a cada paso del mapa
- ✅ Expande todos los desplegables detectados
- ✅ Hace scroll progresivo (300px) para capturar todos los campos
- ✅ Extrae metadatos completos usando atributos `data-controlid`
- ✅ Evita duplicados con set de IDs procesados

**Salida**: Lista de campos con metadatos completos:
```json
{
  "success": true,
  "total_fields": 145,
  "fields": [
    {
      "id": "10917032",
      "control_id": "10917032_0",
      "codigo": "datos_generales_proyecto_nombre_proyecto",
      "label": "Título del Proyecto",
      "type": "textarea",
      "required": true,
      "max_length": 1000,
      "step_index": 0,
      "visible": true
    }
  ]
}
```

## 🎯 Características del Sistema Robusto

### 1. Detección Dinámica de Pasos
```javascript
// Lee desde la barra HTML
#BarraPasosContenedor .slick-track > li[id^="BotonPaso_"]
  
// Extrae información:
- data-seccionid: ID único del paso
- data-slick-index: Índice del paso
- <span>: Título del paso
```

### 2. Scroll Progresivo
```python
scroll_step = 300  # Píxeles por iteración
while current_scroll <= scroll_height:
    # Scroll a posición
    container.scrollTop = current_scroll
    
    # Extraer campos visibles
    extract_visible_fields()
    
    current_scroll += scroll_step
```

### 3. Expansión de Desplegables
```python
# Detecta elementos colapsables
collapse_triggers = page.locator('a[data-toggle="collapse"]')

# Expande si está colapsado
for trigger in collapse_triggers:
    if is_collapsed(target):
        trigger.click()
        wait(500)  # Animación
```

### 4. Prevención de Duplicados
```python
existing_ids = {field.id for field in extracted_fields}

for field in visible_fields:
    if field.id not in existing_ids:
        extract_field(field)
        existing_ids.add(field.id)
```

## 🚀 Modos de Ejecución

### Modo Individual: Explorer
```bash
python main.py --mode explore --form-url "URL" --no-headless
```
**Resultado**: Solo mapa estructural (sin extraer contenido)

### Modo Individual: Extract
```bash
python main.py --mode extract --form-url "URL" --no-headless
```
**Ejecuta**: Explorer → Extractor
**Resultado**: Mapa + Campos extraídos

### Modo Individual: Complete
```bash
python main.py --mode complete --form-url "URL" --no-headless
```
**Ejecuta**: Explorer → Extractor → Completer
**Resultado**: Formulario completado

### Modo Individual: Validate
```bash
python main.py --mode validate --form-url "URL" --no-headless
```
**Ejecuta**: Explorer → Extractor → Validator
**Resultado**: Validación de campos obligatorios/opcionales

### Modo Individual: Match
```bash
python main.py --mode match --form-url "URL" --no-headless
```
**Ejecuta**: Explorer → Extractor → Validator → Matcher
**Resultado**: Matching con campos QA

### Modo Full (Secuencia Completa)
```bash
python main.py --mode full --form-url "URL" --no-headless
```
**Ejecuta**: Explorer → Extractor → Completer → Validator → Matcher → Reporter
**Resultado**: Informe completo en JSON y Markdown

## 🔧 Detalles Técnicos

### Selectores Específicos CORFO
```python
# Barra de pasos
"#BarraPasosContenedor .slick-track"

# Contenedor de formulario
"#seccionRender"

# Campos con metadatos
"input[data-controlid]"
"textarea[data-controlid]"
"select[data-controlid]"

# Desplegables
"a[data-toggle='collapse']"

# Botón siguiente
"#BotonSig"

# Botón guardar
"#btnGuardar"
```

### Atributos Extraídos
Cada campo captura:
- `data-controlid`: ID único del control
- `data-codigo`: Código semántico del campo
- `data-nivel`: Nivel de jerarquía
- `data-orden`: Orden de aparición
- `required`: Si es obligatorio
- `maxlength`: Longitud máxima
- `label`: Etiqueta visual asociada

## 📊 Flujo de Datos

```
┌─────────────┐
│  Explorer   │  Detecta estructura (pasos, desplegables)
└──────┬──────┘
       │ Mapa estructural
       ▼
┌─────────────┐
│  Extractor  │  Expande desplegables + Scroll + Extrae campos
└──────┬──────┘
       │ Lista de campos
       ▼
┌─────────────┐
│  Completer  │  Completa campos con datos de prueba
└──────┬──────┘
       │ Campos completados
       ▼
┌─────────────┐
│  Validator  │  Identifica obligatorios/opcionales
└──────┬──────┘
       │ Clasificación
       ▼
┌─────────────┐
│   Matcher   │  Match con campos QA esperados
└──────┬──────┘
       │ Matching + Gaps
       ▼
┌─────────────┐
│  Reporter   │  Genera informes finales
└─────────────┘
```

## 🛡️ Robustez

### Adaptabilidad
- ✅ No hardcodea cantidad de pasos
- ✅ No hardcodea cantidad de preguntas
- ✅ No hardcodea cantidad de desplegables
- ✅ Se adapta a formularios con diferentes estructuras

### Manejo de Errores
- ✅ Timeout configurables por operación
- ✅ Retry automático en navegación
- ✅ Fallback si scroll falla (extrae directamente)
- ✅ Continúa si un desplegable no se puede expandir
- ✅ Salta campos que no se pueden extraer

### Prevención de Bucles
- ✅ Loop detector por estado de página
- ✅ Límite de pasos por seguridad
- ✅ Set de IDs para evitar re-extraer campos

## 📝 Logs y Debugging

El sistema genera logs detallados:
```
[Explorer] ✓ Detectados 7 pasos en la barra de navegación
[Explorer] --- Mapeando paso 1/7: Datos Generales Proyecto ---
[Explorer] ✓ Paso mapeado: 3 desplegables detectados
[Extractor] --- Extrayendo paso 1/7: Datos Generales Proyecto ---
[Extractor] Expandiendo 3 desplegables...
[Extractor] ✓ Desplegable expandido: Resumen estructura presupuestaria
[Extractor] Iniciando scroll progresivo (altura: 2450px)
[Extractor] ✓ Paso completado: 45 campos extraídos
```

## 🎓 Lecciones Aprendidas

1. **Separación de responsabilidades** es crítica para mantenibilidad
2. **Scroll progresivo** necesario para formularios largos
3. **Desplegables** deben detectarse y expandirse antes de extraer
4. **Duplicados** son comunes con scroll, usar sets para prevenir
5. **Mapa estructural** permite que otros modos sean más eficientes

