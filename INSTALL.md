# Guía de Instalación

## Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Conexión a Internet

## Instalación Paso a Paso

### 1. Clonar o descargar el proyecto

```bash
cd crawlee-corfo
```

### 2. Crear entorno virtual (recomendado)

**En Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**En Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar navegadores de Playwright

```bash
playwright install chromium
```

**Nota:** Si solo necesitas Chromium (recomendado para producción), usa el comando anterior. Para instalar todos los navegadores:

```bash
playwright install
```

### 5. Crear archivos de configuración

Copia el archivo de ejemplo:

```bash
# En Windows
copy .env.example .env

# En Linux/Mac
cp .env.example .env
```

Edita `.env` con tus configuraciones para CORFO:

```env
# URL del formulario objetivo
FORM_URL=https://convocatoria.corfo.cl/formulario

# Credenciales de prueba (opcional)
# TEST_USERNAME debe ser un RUT con formato XX.XXX.XXX-X
TEST_USERNAME=12.345.678-9
TEST_PASSWORD=tu_password_corfo

# Configuración
HEADLESS=false
EVIDENCE_ENABLED=true
```

**Importante:** 
- El agente detectará automáticamente si la página requiere login
- Si detecta login, ejecutará automáticamente el flujo de CORFO:
  1. Click en "¿Tienes clave Corfo? Inicia sesión aquí"
  2. Ingreso de RUT y contraseña
  3. Click en "Nueva Postulación +"
- El RUT debe estar en formato chileno: XX.XXX.XXX-X
- Si no hay credenciales, continuará sin login

### 6. Crear PDF de prueba

```bash
python create_sample_pdf.py
```

### 7. Verificar instalación

Ejecuta una validación de ejemplo:

```bash
python main.py --mode explore --form-url https://ejemplo.com --no-headless
```

## Solución de Problemas

### Error: "No module named 'crawlee'"

Asegúrate de haber activado el entorno virtual e instalado las dependencias:

```bash
pip install -r requirements.txt
```

### Error al instalar Playwright

Si tienes problemas instalando navegadores, intenta:

```bash
python -m playwright install chromium
```

### Problemas con encoding en Windows

Si ves errores de encoding, asegúrate de que tu terminal use UTF-8:

```bash
chcp 65001
```

O ejecuta los scripts desde PowerShell moderno.

### PDF de prueba no se crea

Si `reportlab` no está instalado, se creará un PDF básico automáticamente. Para un PDF completo:

```bash
pip install reportlab
python create_sample_pdf.py
```

## Configuración Avanzada

### Usar diferentes navegadores

Edita `config.py` o configura en `.env`:

```env
BROWSER_TYPE=firefox  # o webkit
```

### Ajustar timeouts

```env
TIMEOUT_DEFAULT=30000
TIMEOUT_NAVIGATION=60000
```

### Personalizar campos QA

Edita `test_data/campos_corfo.txt` con tus campos específicos.

## Próximos Pasos

1. Lee el [README.md](README.md) para entender la arquitectura
2. Revisa [run_example.py](run_example.py) para ver ejemplos de uso
3. Ejecuta una validación completa de tu formulario

## Soporte

Para problemas o preguntas:
- Revisa los logs en `agent.log`
- Verifica la configuración en `.env`
- Ejecuta con `--no-headless` para ver qué está pasando

