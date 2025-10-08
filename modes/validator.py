"""
Modo Validator: Detecta obligatoriedad de campos mediante múltiples señales.
Verifica atributos, visuales, validaciones runtime y mensajes de error.
"""

import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import Page

from modes.extractor import FormField
from utils.selectors import SelectorStrategy
from config import COMMON_SELECTORS, REQUIRED_KEYWORDS

logger = logging.getLogger(__name__)


class ValidationEvent:
    """Representa un evento de validación (intento de avanzar, error, etc.)"""
    
    def __init__(
        self,
        field_key: str,
        event_type: str,
        success: bool,
        message: Optional[str] = None,
        screenshot: Optional[str] = None
    ):
        """
        Inicializa un evento de validación.
        
        Args:
            field_key: Clave canónica del campo
            event_type: Tipo de evento ('blur', 'submit_attempt', 'validation_error')
            success: Si la validación pasó
            message: Mensaje de error/validación
            screenshot: Ruta al screenshot de evidencia
        """
        self.field_key = field_key
        self.event_type = event_type
        self.success = success
        self.message = message
        self.screenshot = screenshot
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a diccionario"""
        return {
            "field_key": self.field_key,
            "event_type": self.event_type,
            "success": self.success,
            "message": self.message,
            "screenshot": self.screenshot
        }


class Validator:
    """Modo Validator: Detecta obligatoriedad mediante múltiples señales"""
    
    def __init__(self, page: Page, config, fields: List[FormField]):
        """
        Inicializa el validador.
        
        Args:
            page: Página de Playwright
            config: Configuración del agente
            fields: Lista de campos extraídos
        """
        self.page = page
        self.config = config
        self.fields = fields
        self.selector_strategy = SelectorStrategy(page, config.timeout_element)
        
        # Resultados
        self.validation_events: List[ValidationEvent] = []
        self.required_fields: List[str] = []
        self.optional_fields: List[str] = []
        self.uncertain_fields: List[str] = []
    
    async def validate(self) -> Dict[str, Any]:
        """
        Ejecuta el modo Validator completo.
        
        Returns:
            Diccionario con resultados de validación
        """
        logger.info("=== Iniciando modo Validator ===")
        
        try:
            for field in self.fields:
                # Saltar campos no editables
                if not field.visible or not field.enabled:
                    continue
                
                # Detectar obligatoriedad
                is_required = await self._detect_required(field)
                
                if is_required is True:
                    self.required_fields.append(field.canonical_key)
                elif is_required is False:
                    self.optional_fields.append(field.canonical_key)
                else:
                    # Incierto
                    self.uncertain_fields.append(field.canonical_key)
            
            # Intentar validar el formulario (sin enviarlo realmente)
            await self._test_form_validation()
            
            logger.info(
                f"Validación completada: {len(self.required_fields)} obligatorios, "
                f"{len(self.optional_fields)} opcionales, "
                f"{len(self.uncertain_fields)} inciertos"
            )
            
            return {
                "success": True,
                "required_fields": self.required_fields,
                "optional_fields": self.optional_fields,
                "uncertain_fields": self.uncertain_fields,
                "validation_events": [event.to_dict() for event in self.validation_events],
                "total_fields": len(self.fields)
            }
            
        except Exception as e:
            logger.error(f"Error en modo Validator: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "required_fields": self.required_fields,
                "optional_fields": self.optional_fields
            }
    
    async def _detect_required(self, field: FormField) -> Optional[bool]:
        """
        Detecta si un campo es obligatorio usando múltiples señales.
        
        Args:
            field: Campo a validar
            
        Returns:
            True si es obligatorio, False si es opcional, None si es incierto
        """
        signals = []
        
        # Señal 1: Atributo HTML 'required'
        if field.required_flag:
            signals.append(("html_required", True))
            logger.debug(f"{field.canonical_key}: HTML required attribute")
        
        # Señal 2: aria-required
        if field.aria_required is True:
            signals.append(("aria_required", True))
            logger.debug(f"{field.canonical_key}: ARIA required")
        
        # Señal 3: Asterisco en label
        if field.label_visible:
            if "*" in field.label_visible or "(*)" in field.label_visible:
                signals.append(("asterisk", True))
                logger.debug(f"{field.canonical_key}: Asterisk in label")
        
        # Señal 4: Palabras clave en label o help text
        combined_text = " ".join(filter(None, [
            field.label_visible,
            field.help_text,
            field.aria_label
        ])).lower()
        
        for keyword in REQUIRED_KEYWORDS:
            if keyword in combined_text:
                signals.append(("keyword", True))
                logger.debug(f"{field.canonical_key}: Required keyword found")
                break
        
        # Señal 5: Validación pattern o min/max restrictivos
        if field.pattern or field.min_length or field.min_value:
            signals.append(("validation_rules", True))
            logger.debug(f"{field.canonical_key}: Has validation rules")
        
        # Señal 6: Probar blur y verificar cambios
        blur_required = await self._test_blur_validation(field)
        if blur_required is not None:
            signals.append(("blur_test", blur_required))
        
        # Determinar resultado final
        if not signals:
            # Sin señales, asumir opcional por defecto
            return False
        
        # Contar señales positivas
        positive_signals = sum(1 for _, required in signals if required)
        
        # Si hay al menos 2 señales positivas, es obligatorio
        if positive_signals >= 2:
            return True
        elif positive_signals >= 1:
            # Una sola señal: incierto (depende del contexto)
            return None
        else:
            return False
    
    async def _test_blur_validation(self, field: FormField) -> Optional[bool]:
        """
        Prueba si el campo muestra error al perder foco estando vacío.
        
        Args:
            field: Campo a probar
            
        Returns:
            True si muestra error (obligatorio), False si no, None si no se pudo determinar
        """
        try:
            # Localizar el campo
            locator = self.page.locator(field.selector).first
            
            # Asegurar que está visible
            is_visible = await locator.is_visible(timeout=2000)
            if not is_visible:
                return None
            
            # Hacer focus en el campo
            await locator.focus()
            await self.page.wait_for_timeout(500)
            
            # Quitar focus (blur)
            await self.page.keyboard.press("Tab")
            await self.page.wait_for_timeout(500)
            
            # Verificar si aparece mensaje de error o aria-invalid
            aria_invalid = await locator.get_attribute("aria-invalid")
            if aria_invalid == "true":
                logger.debug(f"{field.canonical_key}: aria-invalid after blur")
                return True
            
            # Buscar mensaje de error cercano
            error_found = await self._check_error_message_nearby(locator)
            if error_found:
                logger.debug(f"{field.canonical_key}: Error message after blur")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error en test de blur para {field.canonical_key}: {e}")
            return None
    
    async def _check_error_message_nearby(self, locator) -> bool:
        """
        Verifica si hay un mensaje de error cerca del campo.
        
        Args:
            locator: Locator del campo
            
        Returns:
            True si encuentra mensaje de error
        """
        error_selectors = COMMON_SELECTORS["error_message"]
        
        for selector in error_selectors:
            try:
                # Buscar siguiente elemento de error
                error_element = locator.locator(f'xpath=following-sibling::{selector}[1]')
                is_visible = await error_element.is_visible(timeout=1000)
                
                if is_visible:
                    return True
                    
            except Exception:
                continue
        
        return False
    
    async def _test_form_validation(self) -> None:
        """
        Intenta avanzar en el formulario vacío para provocar errores de validación.
        Esto ayuda a confirmar qué campos son realmente obligatorios.
        """
        logger.info("Probando validación del formulario...")
        
        try:
            # Tomar screenshot del estado inicial
            if self.config.evidence_enabled:
                screenshot_path = await self._take_screenshot("before_validation")
            else:
                screenshot_path = None
            
            # Buscar botón de "Siguiente" o "Enviar"
            next_button = await self.selector_strategy.find_element(
                COMMON_SELECTORS["next_button"] + COMMON_SELECTORS["submit_button"],
                visible=True
            )
            
            if not next_button:
                logger.warning("No se encontró botón de navegación para probar validación")
                return
            
            # Intentar click
            await self.selector_strategy.safe_click(next_button)
            
            # Esperar a que aparezcan mensajes de error
            await self.page.wait_for_timeout(2000)
            
            # Tomar screenshot después del intento
            if self.config.evidence_enabled:
                screenshot_path_after = await self._take_screenshot("after_validation_attempt")
            else:
                screenshot_path_after = None
            
            # Buscar mensajes de error visibles
            await self._collect_validation_errors(screenshot_path_after)
            
            logger.info("Prueba de validación completada")
            
        except Exception as e:
            logger.error(f"Error en prueba de validación del formulario: {e}")
    
    async def _collect_validation_errors(self, screenshot: Optional[str]) -> None:
        """
        Recopila mensajes de error de validación visibles.
        
        Args:
            screenshot: Ruta al screenshot de evidencia
        """
        error_selectors = COMMON_SELECTORS["error_message"]
        
        for selector in error_selectors:
            try:
                error_elements = self.page.locator(selector)
                count = await error_elements.count()
                
                for i in range(count):
                    element = error_elements.nth(i)
                    is_visible = await element.is_visible()
                    
                    if is_visible:
                        text = await element.text_content()
                        if text and text.strip():
                            # Intentar asociar error a un campo
                            field_key = await self._associate_error_to_field(element)
                            
                            event = ValidationEvent(
                                field_key=field_key or "unknown",
                                event_type="validation_error",
                                success=False,
                                message=text.strip(),
                                screenshot=screenshot
                            )
                            self.validation_events.append(event)
                            
                            logger.debug(f"Error de validación encontrado: {text.strip()}")
                            
            except Exception as e:
                logger.debug(f"Error buscando mensajes con selector {selector}: {e}")
    
    async def _associate_error_to_field(self, error_element) -> Optional[str]:
        """
        Intenta asociar un mensaje de error a un campo específico.
        
        Args:
            error_element: Locator del mensaje de error
            
        Returns:
            Clave canónica del campo asociado o None
        """
        try:
            # Buscar campo anterior en el DOM
            field_element = error_element.locator('xpath=preceding-sibling::input[1]')
            field_id = await field_element.get_attribute("id", timeout=1000)
            
            if field_id:
                # Buscar en nuestros campos
                for field in self.fields:
                    if field.id == field_id:
                        return field.canonical_key
            
        except Exception:
            pass
        
        return None
    
    async def _take_screenshot(self, name: str) -> str:
        """
        Toma un screenshot para evidencia.
        
        Args:
            name: Nombre del screenshot
            
        Returns:
            Ruta relativa al screenshot
        """
        try:
            output_paths = self.config.get_output_paths()
            evidence_dir = output_paths["evidence"]
            evidence_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{name}.png"
            filepath = evidence_dir / filename
            
            await self.page.screenshot(path=str(filepath), full_page=True)
            
            # Retornar ruta relativa
            return f"evidence/{filename}"
            
        except Exception as e:
            logger.error(f"Error tomando screenshot: {e}")
            return ""

