# 🤖 Agente de Validación de Formularios Web

Sistema automatizado e inteligente para navegar, extraer, autocompletar y validar formularios web extensos y multi-paso, generando informes detallados de anomalías con evidencias.

> **Diseñado específicamente para formularios CORFO, pero adaptable a cualquier formulario web complejo.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Crawlee](https://img.shields.io/badge/Crawlee-0.3%2B-green.svg)](https://crawlee.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-red.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Características

- **Navegación robusta multi-paso**: Recorre formularios con 7-14+ secciones
- **Extracción estructurada**: Captura todos los campos con metadatos completos
- **Detección de obligatoriedad**: Múltiples señales (atributos, visuales, validaciones)
- **Autocompletado inteligente**: Datos de prueba coherentes por tipo de campo
- **Matching QA**: Compara contra lista de Campos Fundamentales
- **Reportes completos**: JSON estructurado + informe legible + evidencias

## Modos de Operación

1. **Explorer**: Mapea estructura del formulario (pasos, secciones, botones)
2. **Extractor**: Registra campos con metadatos detallados
3. **Completer**: Rellena formulario con datos de prueba
4. **Validator**: Verifica reglas y obligatoriedad
5. **Matcher QA**: Cruza con Campos Fundamentales
6. **Reporter**: Genera informes y evidencias

## Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Instalar navegadores de Playwright
playwright install chromium
```

## 🚀 Inicio Rápido

### Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Instalar navegadores de Playwright
playwright install chromium

# Crear PDF de prueba
python create_sample_pdf.py
```

### Primera Validación

```bash
# Explorar un formulario (navegador visible)
python main.py --mode explore --form-url "https://tu-formulario.com" --no-headless

# Validación completa con evidencia
python main.py --mode full --form-url "https://tu-formulario.com" --evidence
```

📖 **Guía completa:** [QUICKSTART.md](QUICKSTART.md)

## 💡 Uso Avanzado

```bash
# Ejecución completa (todos los modos)
python main.py --mode full --form-url "URL" --qa-fields campos_corfo.txt

# Solo explorar estructura
python main.py --mode explore --form-url "URL"

# Detectar obligatoriedad
python main.py --mode validate --form-url "URL" --evidence

# Comparar con lista QA
python main.py --mode match --form-url "URL" --qa-fields mis_campos.txt

# Headless (para CI/CD)
python main.py --mode full --form-url "URL"
```

📖 **Más ejemplos:** [USAGE.md](USAGE.md)

## Estructura del Proyecto

```
crawlee-corfo/
├── main.py                    # Punto de entrada principal
├── config.py                  # Configuración y parámetros
├── data_generator.py          # Generador de datos de prueba
├── modes/
│   ├── explorer.py            # Modo Explorer
│   ├── extractor.py           # Modo Extractor
│   ├── completer.py           # Modo Completer
│   ├── validator.py           # Modo Validator
│   └── matcher.py             # Matcher QA
├── reporter.py                # Generación de reportes
├── utils/
│   ├── selectors.py           # Estrategias de selectores
│   ├── normalizer.py          # Normalización de texto
│   └── resilience.py          # Heurísticas de resiliencia
├── test_data/
│   ├── campos_corfo.txt       # Campos Fundamentales QA
│   └── sample.pdf             # PDF de prueba para uploads
└── outputs/                   # Resultados generados
    ├── json/                  # JSON estructurados
    ├── reports/               # Informes legibles
    └── evidence/              # Screenshots
```

## Configuración

Crea un archivo `.env` con tus parámetros:

```env
TEST_USERNAME=usuario_prueba
TEST_PASSWORD=password_prueba
HEADLESS=true
EVIDENCE_ENABLED=true
```

## Salidas

### JSON Estructurado
- `form_overview`: Metadatos del formulario
- `fields[]`: Todos los campos con metadatos
- `validation_events[]`: Intentos de validación
- `qa_match[]`: Estado de matching QA
- `anomalies[]`: Anomalías detectadas

### Informe Legible
- Resumen ejecutivo
- Métricas de cobertura
- Lista de anomalías con evidencia
- Propuestas de mejora

### Evidencias
- Screenshots por paso
- Logs de ejecución detallados

## 📊 Resultados Esperados

En un formulario típico de CORFO (7-14 pasos, 40-60 campos):

- ⏱️ **Tiempo:** 10-20 minutos (modo full)
- 📝 **Extracción:** 100% de campos visibles
- ✏️ **Autocompletado:** >95% de campos
- ✅ **Precisión obligatoriedad:** >90%
- 📈 **Cobertura QA:** Variable (objetivo: >85%)

## 📚 Documentación

- 📘 **[QUICKSTART.md](QUICKSTART.md)** - Empieza en 5 minutos
- 📗 **[INSTALL.md](INSTALL.md)** - Instalación detallada
- 📕 **[USAGE.md](USAGE.md)** - Guía de uso completa
- 📙 **[ARCHITECTURE.md](ARCHITECTURE.md)** - Diseño del sistema
- 📄 **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Resumen ejecutivo

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Áreas de mejora:

- Login automático genérico
- ML para matching más inteligente
- Validaciones de reglas de negocio
- API REST
- Dashboard web
- Soporte multiidioma

## 📝 Licencia

MIT

## 🙋 Soporte

- 📖 Lee la documentación en la carpeta raíz
- 🐛 Reporta bugs con información detallada
- 💬 Revisa `agent.log` para debugging
- 📸 Usa `--evidence` para capturar screenshots

---

**Desarrollado con ❤️ para la comunidad de validación de formularios web**

