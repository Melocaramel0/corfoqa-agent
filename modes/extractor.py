"""
Modo Extractor: Extrae todos los campos del formulario con sus metadatos completos.
Captura tipo, etiquetas, validaciones, opciones, visibilidad y más.
"""

import logging
import re
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, Locator

from utils.selectors import SelectorStrategy
from utils.normalizer import normalize_text, get_canonical_key
from config import FIELD_TYPES, REQUIRED_KEYWORDS

logger = logging.getLogger(__name__)


class FormField:
    """Representa un campo de formulario con todos sus metadatos"""
    
    def __init__(self):
        """Inicializa un campo vacío"""
        # Identificación
        self.id: Optional[str] = None
        self.name: Optional[str] = None
        self.type: str = "unknown"
        
        # Etiquetas y textos
        self.label_visible: Optional[str] = None
        self.label_for: Optional[str] = None
        self.placeholder: Optional[str] = None
        self.help_text: Optional[str] = None
        self.title: Optional[str] = None
        
        # Atributos ARIA
        self.aria_label: Optional[str] = None
        self.aria_labelledby: Optional[str] = None
        self.aria_describedby: Optional[str] = None
        self.aria_required: Optional[bool] = None
        self.aria_invalid: Optional[bool] = None
        
        # Validaciones y restricciones
        self.required_flag: bool = False
        self.pattern: Optional[str] = None
        self.min_value: Optional[str] = None
        self.max_value: Optional[str] = None
        self.min_length: Optional[int] = None
        self.max_length: Optional[int] = None
        self.accept: Optional[str] = None  # Para file inputs
        
        # Opciones (para select, radio, checkbox)
        self.options: List[str] = []
        self.multiple: bool = False
        
        # Contexto
        self.section: Optional[str] = None
        self.step_index: Optional[int] = None
        self.order: int = 0
        
        # Estado
        self.visible: bool = True
        self.enabled: bool = True
        self.readonly: bool = False
        
        # Selector
        self.selector: Optional[str] = None
        
        # Clave canónica para matching
        self.canonical_key: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el campo a diccionario"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "label_visible": self.label_visible,
            "label_for": self.label_for,
            "placeholder": self.placeholder,
            "help_text": self.help_text,
            "title": self.title,
            "aria_label": self.aria_label,
            "aria_labelledby": self.aria_labelledby,
            "aria_describedby": self.aria_describedby,
            "aria_required": self.aria_required,
            "aria_invalid": self.aria_invalid,
            "required_flag": self.required_flag,
            "pattern": self.pattern,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "accept": self.accept,
            "options": self.options,
            "multiple": self.multiple,
            "section": self.section,
            "step_index": self.step_index,
            "order": self.order,
            "visible": self.visible,
            "enabled": self.enabled,
            "readonly": self.readonly,
            "selector": self.selector,
            "canonical_key": self.canonical_key
        }


class Extractor:
    """Modo Extractor: Extrae todos los campos con metadatos completos"""
    
    def __init__(self, page: Page, config, explorer_result: Optional[Dict] = None):
        """
        Inicializa el extractor.
        
        Args:
            page: Página de Playwright
            config: Configuración del agente
            explorer_result: Resultado del modo Explorer (opcional)
        """
        self.page = page
        self.config = config
        self.explorer_result = explorer_result
        self.selector_strategy = SelectorStrategy(page, config.timeout_element)
        
        # Campos extraídos
        self.fields: List[FormField] = []
    
    async def extract(self, step_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Ejecuta la extracción de campos.
        
        Args:
            step_index: Índice del paso a extraer (None = todos los pasos)
            
        Returns:
            Diccionario con todos los campos extraídos
        """
        logger.info("=== Iniciando modo Extractor ===")
        
        try:
            if step_index is not None:
                # Extraer solo un paso específico
                await self._extract_step(step_index)
            elif self.explorer_result and self.explorer_result.get("steps"):
                # Extraer todos los pasos descubiertos por Explorer
                for step in self.explorer_result["steps"]:
                    await self._extract_step(step["index"])
            else:
                # Extraer página actual
                await self._extract_current_page()
            
            logger.info(f"Extracción completada: {len(self.fields)} campos encontrados")
            
            return {
                "success": True,
                "total_fields": len(self.fields),
                "fields": [field.to_dict() for field in self.fields]
            }
            
        except Exception as e:
            logger.error(f"Error en modo Extractor: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "fields": [field.to_dict() for field in self.fields]
            }
    
    async def _extract_step(self, step_index: int) -> None:
        """
        Extrae campos de un paso específico.
        
        Args:
            step_index: Índice del paso
        """
        logger.info(f"Extrayendo campos del paso {step_index}...")
        
        # Obtener todos los campos del paso
        fields = await self._get_all_fields()
        
        for i, locator in enumerate(fields):
            try:
                field = await self._extract_field(locator, step_index, i)
                if field:
                    self.fields.append(field)
            except Exception as e:
                logger.warning(f"Error extrayendo campo {i}: {e}")
    
    async def _extract_current_page(self) -> None:
        """Extrae campos de la página actual"""
        logger.info("Extrayendo campos de la página actual...")
        await self._extract_step(0)
    
    async def _get_all_fields(self) -> List[Locator]:
        """
        Obtiene todos los campos de formulario visibles.
        
        Returns:
            Lista de locators de campos
        """
        return await self.selector_strategy.get_all_form_fields()
    
    async def _extract_field(
        self,
        locator: Locator,
        step_index: int,
        order: int
    ) -> Optional[FormField]:
        """
        Extrae metadatos completos de un campo.
        
        Args:
            locator: Locator del campo
            step_index: Índice del paso
            order: Orden del campo en el formulario
            
        Returns:
            FormField con todos los metadatos o None si falla
        """
        field = FormField()
        field.step_index = step_index
        field.order = order
        
        try:
            # Atributos básicos
            field.id = await locator.get_attribute("id")
            field.name = await locator.get_attribute("name")
            field.type = await self._detect_field_type(locator)
            field.placeholder = await locator.get_attribute("placeholder")
            field.title = await locator.get_attribute("title")
            
            # Atributos ARIA
            field.aria_label = await locator.get_attribute("aria-label")
            field.aria_labelledby = await locator.get_attribute("aria-labelledby")
            field.aria_describedby = await locator.get_attribute("aria-describedby")
            
            aria_required = await locator.get_attribute("aria-required")
            field.aria_required = aria_required == "true" if aria_required else None
            
            aria_invalid = await locator.get_attribute("aria-invalid")
            field.aria_invalid = aria_invalid == "true" if aria_invalid else None
            
            # Atributo required
            required_attr = await locator.get_attribute("required")
            field.required_flag = required_attr is not None
            
            # Validaciones
            field.pattern = await locator.get_attribute("pattern")
            field.min_value = await locator.get_attribute("min")
            field.max_value = await locator.get_attribute("max")
            
            minlength = await locator.get_attribute("minlength")
            field.min_length = int(minlength) if minlength else None
            
            maxlength = await locator.get_attribute("maxlength")
            field.max_length = int(maxlength) if maxlength else None
            
            field.accept = await locator.get_attribute("accept")
            
            # Multiple (para select y file)
            multiple_attr = await locator.get_attribute("multiple")
            field.multiple = multiple_attr is not None
            
            # Estado
            field.visible = await locator.is_visible()
            field.enabled = await locator.is_enabled()
            
            readonly_attr = await locator.get_attribute("readonly")
            field.readonly = readonly_attr is not None
            
            # Etiqueta visible (buscar label asociado)
            field.label_visible = await self._find_label(locator, field.id)
            
            # Help text (buscar texto de ayuda cercano)
            field.help_text = await self._find_help_text(locator, field.aria_describedby)
            
            # Opciones (para select, radio, checkbox)
            if field.type in ["select", "radio", "checkbox"]:
                field.options = await self._extract_options(locator, field.type)
            
            # Generar selector único
            field.selector = await self._generate_selector(locator, field)
            
            # Generar clave canónica para matching
            field.canonical_key = self._generate_canonical_key(field)
            
            logger.debug(f"Campo extraído: {field.canonical_key} (tipo: {field.type})")
            return field
            
        except Exception as e:
            logger.error(f"Error extrayendo campo: {e}")
            return None
    
    async def _detect_field_type(self, locator: Locator) -> str:
        """
        Detecta el tipo de campo.
        
        Args:
            locator: Locator del campo
            
        Returns:
            Tipo de campo
        """
        # Obtener tag name
        tag_name = await locator.evaluate("el => el.tagName.toLowerCase()")
        
        if tag_name == "select":
            return "select"
        elif tag_name == "textarea":
            return "textarea"
        elif tag_name == "input":
            # Obtener tipo de input
            input_type = await locator.get_attribute("type")
            if input_type and input_type.lower() in FIELD_TYPES:
                return input_type.lower()
            return "text"  # Por defecto
        
        # Verificar roles ARIA
        role = await locator.get_attribute("role")
        if role:
            if role == "textbox":
                return "text"
            elif role == "combobox":
                return "select"
        
        return "unknown"
    
    async def _find_label(self, locator: Locator, field_id: Optional[str]) -> Optional[str]:
        """
        Encuentra la etiqueta (label) asociada al campo.
        
        Args:
            locator: Locator del campo
            field_id: ID del campo
            
        Returns:
            Texto de la etiqueta o None
        """
        # Intentar con label[for="id"]
        if field_id:
            try:
                label = self.page.locator(f'label[for="{field_id}"]')
                text = await label.text_content(timeout=1000)
                if text:
                    return text.strip()
            except Exception:
                pass
        
        # Intentar con label que contiene el input
        try:
            label = locator.locator('xpath=ancestor::label')
            text = await label.text_content(timeout=1000)
            if text:
                return text.strip()
        except Exception:
            pass
        
        # Buscar label cercano por posición
        try:
            # Buscar label anterior en el DOM
            label = locator.locator('xpath=preceding-sibling::label[1]')
            text = await label.text_content(timeout=1000)
            if text:
                return text.strip()
        except Exception:
            pass
        
        return None
    
    async def _find_help_text(
        self,
        locator: Locator,
        aria_describedby: Optional[str]
    ) -> Optional[str]:
        """
        Encuentra texto de ayuda asociado al campo.
        
        Args:
            locator: Locator del campo
            aria_describedby: ID del elemento que describe el campo
            
        Returns:
            Texto de ayuda o None
        """
        # Intentar con aria-describedby
        if aria_describedby:
            try:
                help_element = self.page.locator(f'#{aria_describedby}')
                text = await help_element.text_content(timeout=1000)
                if text:
                    return text.strip()
            except Exception:
                pass
        
        # Buscar elementos comunes de ayuda cercanos
        help_selectors = [
            '.help-text',
            '.help-block',
            '.form-text',
            '.field-hint',
            'small',
            '.description'
        ]
        
        for selector in help_selectors:
            try:
                # Buscar siguiente elemento con clase de ayuda
                help_element = locator.locator(f'xpath=following-sibling::{selector}[1]')
                text = await help_element.text_content(timeout=1000)
                if text:
                    return text.strip()
            except Exception:
                continue
        
        return None
    
    async def _extract_options(self, locator: Locator, field_type: str) -> List[str]:
        """
        Extrae opciones de un campo select, radio o checkbox group.
        
        Args:
            locator: Locator del campo
            field_type: Tipo de campo
            
        Returns:
            Lista de opciones
        """
        options = []
        
        try:
            if field_type == "select":
                # Obtener todas las opciones del select
                option_locators = locator.locator('option')
                count = await option_locators.count()
                
                for i in range(count):
                    option = option_locators.nth(i)
                    text = await option.text_content()
                    value = await option.get_attribute('value')
                    
                    if text and text.strip():
                        options.append(text.strip())
                    elif value:
                        options.append(value)
            
            elif field_type in ["radio", "checkbox"]:
                # Para radio/checkbox, buscar opciones con el mismo name
                name = await locator.get_attribute('name')
                if name:
                    same_name = self.page.locator(f'input[name="{name}"]')
                    count = await same_name.count()
                    
                    for i in range(count):
                        option = same_name.nth(i)
                        # Buscar label asociado
                        option_id = await option.get_attribute('id')
                        if option_id:
                            label = self.page.locator(f'label[for="{option_id}"]')
                            text = await label.text_content(timeout=1000)
                            if text:
                                options.append(text.strip())
        
        except Exception as e:
            logger.debug(f"Error extrayendo opciones: {e}")
        
        return options
    
    async def _generate_selector(self, locator: Locator, field: FormField) -> str:
        """
        Genera un selector único y robusto para el campo.
        
        Args:
            locator: Locator del campo
            field: Campo con metadatos
            
        Returns:
            Selector CSS
        """
        # Preferir ID si existe
        if field.id:
            return f'#{field.id}'
        
        # Usar name si existe
        if field.name:
            return f'[name="{field.name}"]'
        
        # Usar aria-label si existe
        if field.aria_label:
            return f'[aria-label="{field.aria_label}"]'
        
        # Usar placeholder
        if field.placeholder:
            return f'[placeholder="{field.placeholder}"]'
        
        # Por defecto, usar tipo y orden
        return f'{field.type}:nth-of-type({field.order + 1})'
    
    def _generate_canonical_key(self, field: FormField) -> str:
        """
        Genera una clave canónica para matching QA.
        
        Args:
            field: Campo con metadatos
            
        Returns:
            Clave canónica normalizada
        """
        # Usar la etiqueta visible si está disponible
        if field.label_visible:
            return get_canonical_key(field.label_visible)
        
        # Usar aria-label
        if field.aria_label:
            return get_canonical_key(field.aria_label)
        
        # Usar placeholder
        if field.placeholder:
            return get_canonical_key(field.placeholder)
        
        # Usar name
        if field.name:
            return get_canonical_key(field.name)
        
        # Último recurso: usar help text
        if field.help_text:
            return get_canonical_key(field.help_text)
        
        return f"unknown_field_{field.order}"

