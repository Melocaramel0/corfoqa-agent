# Datos de Prueba

Este directorio contiene los datos de prueba necesarios para el agente.

## Archivos

### campos_corfo.txt
Lista de Campos Fundamentales QA para formularios CORFO. Esta es la fuente autoritativa para el matching QA.

### sample.pdf
PDF de prueba para campos de tipo file upload.

**Nota:** Este archivo debe ser creado manualmente o se puede usar cualquier PDF válido disponible en el sistema.

## Uso

El agente utiliza estos archivos automáticamente según la configuración en `config.py` o variables de entorno.

Para usar archivos personalizados:

```bash
python main.py --qa-fields ruta/a/campos.txt --form-url URL_DEL_FORMULARIO
```

O configurar en `.env`:

```
QA_FIELDS_PATH=test_data/campos_corfo.txt
TEST_PDF_PATH=test_data/sample.pdf
```

