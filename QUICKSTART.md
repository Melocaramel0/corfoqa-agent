# 🚀 Inicio Rápido

Pon en marcha el Agente de Validación de Formularios en menos de 5 minutos.

## ⚡ Instalación Rápida

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Instalar navegador

```bash
playwright install chromium
```

### 3. Crear PDF de prueba

```bash
python create_sample_pdf.py
```

## ⚙️ Configuración para CORFO

Crea un archivo `.env` con tus credenciales:

```env
# URL del formulario objetivo (opcional)
FORM_URL=https://convocatoria.corfo.cl/formulario

# Credenciales (RUT y CLAVE)
TEST_USERNAME=123456789
TEST_PASSWORD=tu_password

# Configuración
HEADLESS=false
EVIDENCE_ENABLED=true
```

## 🎯 Primera Validación

### Explorar un formulario CORFO

```bash
python main.py --mode explore --form-url "https://convocatoria.corfo.cl/formulario" --no-headless
```

**Nota:** El agente detectará automáticamente si necesita login. Si configuras credenciales en `.env`:
1. Irá a la URL del formulario
2. Detectará si hay login requerido
3. Si es necesario, hará click en "¿Tienes clave Corfo? Inicia sesión aquí"
4. Ingresará RUT y contraseña
5. Hará click en "Nueva Postulación +"
6. Comenzará a explorar el formulario

Esto:
- ✓ Abre el navegador (visible)
- ✓ Navega al formulario
- ✓ Descubre todos los pasos
- ✓ Muestra la estructura encontrada

### Validación completa

```bash
python main.py --mode full --form-url https://tu-formulario.com --no-headless --evidence
```

Esto:
- ✓ Explora la estructura
- ✓ Extrae todos los campos
- ✓ Autocompleta el formulario
- ✓ Detecta campos obligatorios
- ✓ Compara con lista QA
- ✓ Genera informes completos
- ✓ Captura screenshots

## 📋 Resultados

Los resultados se guardan en:

```
outputs/
├── json/
│   └── report_20241007_203000.json    (Datos estructurados)
├── reports/
│   └── report_20241007_203000.md      (Informe legible)
└── evidence/
    ├── before_validation.png          (Screenshots)
    └── after_validation_attempt.png
```

### Ver informe Markdown

```bash
# Windows
notepad outputs\reports\report_*.md

# Linux/Mac
cat outputs/reports/report_*.md
```

### Ver JSON

```bash
# Windows
type outputs\json\report_*.json

# Linux/Mac
cat outputs/json/report_*.json | jq .
```

## 🛠️ Personalización Básica

### 1. Configurar tus campos QA

Edita `test_data/campos_corfo.txt`:

```txt
# Mis Campos QA
RUT
Nombre
Email
Teléfono
Proyecto
Monto
```

### 2. Ejecutar matching

```bash
python main.py --mode match --form-url https://tu-formulario.com
```

### 3. Ver campos faltantes

El informe Markdown mostrará:
- ✓ Campos QA presentes
- ⚠️ Campos QA faltantes
- 🔍 Campos potencialmente equivalentes

## 🎨 Ejemplos Comunes

### Solo ver estructura (sin completar)

```bash
python main.py --mode explore --form-url URL --no-headless
```

### Detectar campos obligatorios

```bash
python main.py --mode validate --form-url URL --evidence
```

### Comparar con especificación QA

```bash
python main.py --mode match --form-url URL --qa-fields mis_campos.txt
```

### Ejecución rápida (headless)

```bash
python main.py --mode full --form-url URL
```

## 🔧 Solución Rápida de Problemas

### Error: "No module named 'crawlee'"

```bash
pip install -r requirements.txt
```

### Error: "playwright not found"

```bash
playwright install chromium
```

### El navegador no se abre con --no-headless

Intenta sin esa opción (headless es el modo por defecto):

```bash
python main.py --mode explore --form-url URL
```

### No encuentra campos

Aumenta el timeout en el comando:

```bash
# Edita config.py y cambia timeout_default de 30000 a 60000
```

## 📖 Siguiente Paso

¿Todo funcionó? Lee la documentación completa:

- 📘 **[README.md](README.md)** - Visión general
- 📗 **[USAGE.md](USAGE.md)** - Guía de uso completa
- 📕 **[ARCHITECTURE.md](ARCHITECTURE.md)** - Cómo funciona por dentro

## 💡 Tips Rápidos

### 1. Siempre empieza con explore

Antes de validaciones complejas, explora el formulario:

```bash
python main.py --mode explore --form-url URL --no-headless
```

### 2. Usa evidence para debugging

Si algo falla, activa evidencia:

```bash
python main.py --mode full --form-url URL --evidence
```

### 3. Revisa los logs

Si hay errores, revisa `agent.log`:

```bash
tail -f agent.log
```

### 4. Modo visible para desarrollo

Usa `--no-headless` para ver qué hace el agente:

```bash
python main.py --mode complete --form-url URL --no-headless
```

### 5. Modo headless para CI/CD

En servidores y pipelines, omite `--no-headless`:

```bash
python main.py --mode full --form-url URL
```

## 🎯 Checklist de Inicio

- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Playwright instalado (`playwright install chromium`)
- [ ] PDF de prueba creado (`python create_sample_pdf.py`)
- [ ] Primera exploración exitosa
- [ ] Campos QA personalizados en `test_data/campos_corfo.txt`
- [ ] Primera validación completa ejecutada
- [ ] Informe generado en `outputs/reports/`

## 🚀 ¡Listo!

Ya puedes validar formularios web complejos de forma automática. 

Para casos de uso avanzados, revisa [USAGE.md](USAGE.md).

---

*¿Problemas? Revisa [INSTALL.md](INSTALL.md) para solución detallada de problemas.*

