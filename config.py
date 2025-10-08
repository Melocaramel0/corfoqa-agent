"""
Configuración y parámetros del Agente de Validación de Formularios.
Centraliza todos los parámetros de ejecución, timeouts, rutas y flags.
"""

import os
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Modo de operación del agente
AgentMode = Literal["explore", "extract", "complete", "validate", "match", "report", "full"]


class Config(BaseModel):
    """Configuración principal del agente"""
    
    # URLs y navegación
    form_url: str = Field(..., description="URL del formulario objetivo")
    
    # Credenciales de prueba (NUNCA usar credenciales reales)
    test_username: Optional[str] = Field(default=None, description="Usuario de prueba")
    test_password: Optional[str] = Field(default=None, description="Contraseña de prueba")
    
    # Modo de operación
    mode: AgentMode = Field(default="full", description="Modo de ejecución del agente")
    
    # Configuración del navegador
    headless: bool = Field(default=True, description="Ejecutar navegador en modo headless")
    browser_type: Literal["chromium", "firefox", "webkit"] = Field(
        default="chromium",
        description="Tipo de navegador"
    )
    viewport_width: int = Field(default=1920, description="Ancho del viewport")
    viewport_height: int = Field(default=1080, description="Alto del viewport")
    
    # Timeouts (en milisegundos)
    timeout_default: int = Field(default=30000, description="Timeout por defecto")
    timeout_navigation: int = Field(default=60000, description="Timeout de navegación")
    timeout_element: int = Field(default=10000, description="Timeout para elementos")
    
    # Reintentos y resiliencia
    max_retries: int = Field(default=3, description="Número máximo de reintentos")
    retry_delay: int = Field(default=2000, description="Delay entre reintentos (ms)")
    
    # Evidencia y logging
    evidence_enabled: bool = Field(default=True, description="Capturar screenshots y evidencia")
    verbose_logging: bool = Field(default=True, description="Logging detallado")
    
    # Rutas de archivos
    qa_fields_path: str = Field(
        default="test_data/campos_corfo.txt",
        description="Ruta al archivo de Campos Fundamentales QA"
    )
    test_pdf_path: str = Field(
        default="test_data/sample.pdf",
        description="Ruta al PDF de prueba para uploads"
    )
    output_dir: str = Field(default="outputs", description="Directorio de salida")
    
    # Estrategias de matching QA
    qa_match_threshold: float = Field(
        default=0.8,
        description="Umbral de similitud para matching (0-1)"
    )
    
    # Tiempos máximos de ejecución
    max_execution_time: int = Field(
        default=1200,  # 20 minutos
        description="Tiempo máximo de ejecución en segundos"
    )
    
    @classmethod
    def from_env(cls) -> "Config":
        """Crea configuración desde variables de entorno"""
        return cls(
            form_url=os.getenv("FORM_URL", ""),
            test_username=os.getenv("TEST_USERNAME"),
            test_password=os.getenv("TEST_PASSWORD"),
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            timeout_default=int(os.getenv("TIMEOUT_DEFAULT", "30000")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            evidence_enabled=os.getenv("EVIDENCE_ENABLED", "true").lower() == "true",
            qa_fields_path=os.getenv("QA_FIELDS_PATH", "test_data/campos_corfo.txt"),
            test_pdf_path=os.getenv("TEST_PDF_PATH", "test_data/sample.pdf"),
            output_dir=os.getenv("OUTPUT_DIR", "outputs"),
        )
    
    def get_output_paths(self) -> dict[str, Path]:
        """Retorna las rutas de salida organizadas"""
        base = Path(self.output_dir)
        return {
            "base": base,
            "json": base / "json",
            "reports": base / "reports",
            "evidence": base / "evidence",
        }
    
    def ensure_directories(self) -> None:
        """Crea los directorios necesarios si no existen"""
        paths = self.get_output_paths()
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)


# Selectores comunes (pueden ser extendidos/modificados según el sitio)
COMMON_SELECTORS = {
    # Botones de navegación
    "next_button": [
        'button:has-text("Siguiente")',
        'button:has-text("Continuar")',
        'button:has-text("Guardar y Continuar")',
        'input[type="submit"][value*="Siguiente"]',
        'input[type="button"][value*="Siguiente"]',
        '[role="button"]:has-text("Siguiente")',
        'a:has-text("Siguiente")',
    ],
    "previous_button": [
        'button:has-text("Anterior")',
        'button:has-text("Volver")',
        'button:has-text("Atrás")',
        '[role="button"]:has-text("Anterior")',
    ],
    "submit_button": [
        'button:has-text("Enviar")',
        'button:has-text("Finalizar")',
        'button:has-text("Completar")',
        'input[type="submit"]',
        '[role="button"]:has-text("Enviar")',
    ],
    # Indicadores de paso
    "step_indicator": [
        '.step-indicator',
        '.wizard-step',
        '.progress-step',
        '[role="progressbar"]',
        '.stepper',
    ],
    # Contenedores de formulario
    "form_container": [
        'form',
        '[role="form"]',
        '.form-container',
        '.wizard-content',
    ],
    # Mensajes de error
    "error_message": [
        '.error',
        '.error-message',
        '[role="alert"]',
        '.invalid-feedback',
        '.field-error',
        '[aria-invalid="true"] + .error',
    ],
}

# Tipos de campo reconocidos
FIELD_TYPES = [
    "text", "email", "tel", "number", "url", "password",
    "date", "time", "datetime-local", "month", "week",
    "select", "multiselect", "radio", "checkbox",
    "textarea", "file", "hidden", "range", "color"
]

# Palabras clave para detectar obligatoriedad
REQUIRED_KEYWORDS = [
    "obligatorio", "requerido", "required", "necesario",
    "debe", "campo obligatorio", "campo requerido"
]

# Stopwords en español para normalización
STOPWORDS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "y", "o", "en", "para", "por",
    "con", "sin", "sobre", "entre", "a"
}

