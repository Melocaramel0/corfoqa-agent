"""
Modo Completer: Autocompleta formularios con datos de prueba coherentes.
Maneja todos los tipos de campos incluyendo uploads de archivos.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from playwright.async_api import Page

from modes.extractor import FormField
from data_generator import DataGenerator
from utils.selectors import SelectorStrategy
from utils.resilience import RetryStrategy, safe_execute

logger = logging.getLogger(__name__)


class Completer:
    """Modo Completer: Autocompleta formularios con datos coherentes"""
    
    def __init__(self, page: Page, config, fields: List[FormField]):
        """
        Inicializa el completer.
        
        Args:
            page: Página de Playwright
            config: Configuración del agente
            fields: Lista de campos extraídos por Extractor
        """
        self.page = page
        self.config = config
        self.fields = fields
        self.selector_strategy = SelectorStrategy(page, config.timeout_element)
        self.retry_strategy = RetryStrategy(max_retries=config.max_retries)
        self.data_generator = DataGenerator(seed=42)  # Seed para reproducibilidad
        
        # Resultados
        self.completed_fields: List[Dict[str, Any]] = []
        self.failed_fields: List[Dict[str, Any]] = []
        
        # Cache de datos generados para coherencia
        self.generated_data: Dict[str, str] = {}
    
    async def complete(self) -> Dict[str, Any]:
        """
        Ejecuta el autocompletado del formulario.
        
        Returns:
            Diccionario con resultados del autocompletado
        """
        logger.info("=== Iniciando modo Completer ===")
        
        try:
            for field in self.fields:
                # Saltar campos readonly, hidden o disabled
                if not field.visible or not field.enabled or field.readonly:
                    logger.debug(f"Saltando campo no editable: {field.canonical_key}")
                    continue
                
                # Completar el campo
                success = await self._complete_field(field)
                
                if success:
                    self.completed_fields.append({
                        "canonical_key": field.canonical_key,
                        "type": field.type,
                        "value": self.generated_data.get(field.canonical_key, "N/A")
                    })
                else:
                    self.failed_fields.append({
                        "canonical_key": field.canonical_key,
                        "type": field.type,
                        "selector": field.selector
                    })
            
            completion_rate = (
                len(self.completed_fields) / len(self.fields) * 100
                if self.fields else 0
            )
            
            logger.info(
                f"Autocompletado completado: {len(self.completed_fields)}/{len(self.fields)} "
                f"campos ({completion_rate:.1f}%)"
            )
            
            return {
                "success": True,
                "total_fields": len(self.fields),
                "completed_fields": len(self.completed_fields),
                "failed_fields": len(self.failed_fields),
                "completion_rate": completion_rate,
                "completed": self.completed_fields,
                "failed": self.failed_fields
            }
            
        except Exception as e:
            logger.error(f"Error en modo Completer: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "completed": self.completed_fields,
                "failed": self.failed_fields
            }
    
    async def _complete_field(self, field: FormField) -> bool:
        """
        Completa un campo individual con datos apropiados.
        
        Args:
            field: Campo a completar
            
        Returns:
            True si se completó exitosamente
        """
        try:
            # Generar valor apropiado según el tipo de campo
            value = self._generate_field_value(field)
            
            if value is None:
                logger.debug(f"No se pudo generar valor para: {field.canonical_key}")
                return False
            
            # Guardar valor generado
            self.generated_data[field.canonical_key] = value
            
            # Localizar el campo
            locator = self.page.locator(field.selector).first
            
            # Completar según el tipo
            if field.type == "select":
                return await self._complete_select(locator, field, value)
            elif field.type in ["radio", "checkbox"]:
                return await self._complete_radio_checkbox(locator, field, value)
            elif field.type == "file":
                return await self._complete_file(locator, field)
            else:
                # Campos de texto, número, email, tel, date, etc.
                return await self._complete_text_field(locator, field, value)
            
        except Exception as e:
            logger.error(f"Error completando campo {field.canonical_key}: {e}")
            return False
    
    def _generate_field_value(self, field: FormField) -> Optional[str]:
        """
        Genera un valor apropiado para el campo según su tipo y contexto.
        
        Args:
            field: Campo para el que generar valor
            
        Returns:
            Valor generado o None
        """
        # Detectar tipo de campo por su clave canónica y etiquetas
        key_lower = (field.canonical_key or "").lower()
        label_lower = (field.label_visible or "").lower()
        combined = f"{key_lower} {label_lower}"
        
        # RUT/RUN
        if any(term in combined for term in ["rut", "run", "rol unico"]):
            return self.data_generator.generate_rut()
        
        # Nombres
        if "nombre completo" in combined:
            return self.data_generator.generate_nombre_completo()
        elif any(term in combined for term in ["primer nombre", "nombre", "nombres"]):
            if "nombre" not in self.generated_data:
                self.generated_data["nombre"] = self.data_generator.generate_nombre()
            return self.generated_data["nombre"]
        
        # Apellidos
        if "apellido paterno" in combined or "primer apellido" in combined:
            if "apellido_paterno" not in self.generated_data:
                self.generated_data["apellido_paterno"] = self.data_generator.generate_apellido_paterno()
            return self.generated_data["apellido_paterno"]
        
        if "apellido materno" in combined or "segundo apellido" in combined:
            if "apellido_materno" not in self.generated_data:
                self.generated_data["apellido_materno"] = self.data_generator.generate_apellido_materno()
            return self.generated_data["apellido_materno"]
        
        # Email
        if any(term in combined for term in ["email", "correo", "mail"]):
            if "email" not in self.generated_data:
                nombre = self.generated_data.get("nombre")
                self.generated_data["email"] = self.data_generator.generate_email(nombre)
            return self.generated_data["email"]
        
        # Teléfono
        if any(term in combined for term in ["telefono", "fono", "celular", "movil"]):
            tipo = "movil" if "celular" in combined or "movil" in combined else "fijo"
            return self.data_generator.generate_telefono(tipo)
        
        # Fechas
        if "fecha" in combined or "date" in field.type:
            if "nacimiento" in combined:
                return self.data_generator.generate_fecha("nacimiento", "%Y-%m-%d")
            elif "inicio" in combined and "actividades" in combined:
                return self.data_generator.generate_fecha("inicio_actividades", "%Y-%m-%d")
            else:
                return self.data_generator.generate_fecha("pasado", "%Y-%m-%d")
        
        # Montos
        if any(term in combined for term in ["monto", "valor", "precio", "costo", "aporte"]):
            moneda = "UF" if "uf" in combined else "CLP"
            return self.data_generator.generate_monto(moneda=moneda)
        
        # Razón social
        if "razon social" in combined or "nombre empresa" in combined:
            if "razon_social" not in self.generated_data:
                self.generated_data["razon_social"] = self.data_generator.generate_razon_social()
            return self.generated_data["razon_social"]
        
        # Giro
        if "giro" in combined or "actividad" in combined or "rubro" in combined:
            return self.data_generator.generate_giro()
        
        # Dirección
        if "direccion" in combined or "calle" in combined:
            if "direccion" not in self.generated_data:
                direccion = self.data_generator.generate_direccion()
                self.generated_data["direccion"] = direccion["direccion_completa"]
                self.generated_data["calle"] = direccion["calle"]
                self.generated_data["numero"] = direccion["numero"]
                self.generated_data["region"] = direccion["region"]
                self.generated_data["comuna"] = direccion["comuna"]
            
            if "calle" in combined:
                return self.generated_data["calle"]
            elif "numero" in combined:
                return self.generated_data["numero"]
            else:
                return self.generated_data["direccion"]
        
        if "region" in combined:
            if "region" not in self.generated_data:
                direccion = self.data_generator.generate_direccion()
                self.generated_data.update({
                    "region": direccion["region"],
                    "comuna": direccion["comuna"]
                })
            return self.generated_data["region"]
        
        if "comuna" in combined:
            if "comuna" not in self.generated_data:
                direccion = self.data_generator.generate_direccion()
                self.generated_data.update({
                    "region": direccion["region"],
                    "comuna": direccion["comuna"]
                })
            return self.generated_data["comuna"]
        
        # Porcentaje
        if "porcentaje" in combined or "%" in combined:
            return self.data_generator.generate_porcentaje()
        
        # Según tipo de input
        if field.type == "email":
            return self.data_generator.generate_email()
        elif field.type == "tel":
            return self.data_generator.generate_telefono()
        elif field.type == "number":
            # Respetar min/max si existen
            min_val = int(field.min_value) if field.min_value else 1
            max_val = int(field.max_value) if field.max_value else 1000
            return self.data_generator.generate_numero(min_val, max_val)
        elif field.type == "url":
            return "https://www.ejemplo.cl"
        elif field.type == "select":
            # Para selects, retornar None (se manejará en _complete_select)
            return None
        elif field.type == "textarea":
            return self.data_generator.generate_texto(10, 30)
        else:
            # Campo de texto genérico
            return self.data_generator.generate_texto(3, 10)
    
    async def _complete_text_field(
        self,
        locator,
        field: FormField,
        value: str
    ) -> bool:
        """
        Completa un campo de texto.
        
        Args:
            locator: Locator del campo
            field: Metadatos del campo
            value: Valor a ingresar
            
        Returns:
            True si se completó exitosamente
        """
        try:
            # Aplicar restricciones de longitud
            if field.max_length and len(value) > field.max_length:
                value = value[:field.max_length]
            
            # Rellenar el campo
            success = await self.selector_strategy.safe_fill(locator, value)
            
            if success:
                logger.debug(f"Campo completado: {field.canonical_key} = {value[:50]}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error rellenando campo de texto: {e}")
            return False
    
    async def _complete_select(
        self,
        locator,
        field: FormField,
        value: Optional[str]
    ) -> bool:
        """
        Completa un campo select.
        
        Args:
            locator: Locator del campo
            field: Metadatos del campo
            value: Valor sugerido (puede ser None)
            
        Returns:
            True si se completó exitosamente
        """
        try:
            if not field.options:
                logger.debug(f"Select sin opciones: {field.canonical_key}")
                return False
            
            # Filtrar opciones vacías o placeholder
            valid_options = [
                opt for opt in field.options
                if opt and opt.lower() not in ["seleccione", "seleccionar", "elige", "elegir", "--", ""]
            ]
            
            if not valid_options:
                logger.debug(f"Select sin opciones válidas: {field.canonical_key}")
                return False
            
            # Seleccionar primera opción válida
            option_to_select = valid_options[0]
            
            # Intentar seleccionar por texto
            await locator.select_option(label=option_to_select, timeout=self.config.timeout_element)
            
            logger.debug(f"Select completado: {field.canonical_key} = {option_to_select}")
            return True
            
        except Exception as e:
            logger.error(f"Error completando select: {e}")
            return False
    
    async def _complete_radio_checkbox(
        self,
        locator,
        field: FormField,
        value: str
    ) -> bool:
        """
        Completa un campo radio o checkbox.
        
        Args:
            locator: Locator del campo
            field: Metadatos del campo
            value: Valor (no usado, siempre marca la primera opción)
            
        Returns:
            True si se completó exitosamente
        """
        try:
            # Para radio/checkbox, simplemente marcar el primero
            is_checked = await locator.is_checked()
            
            if not is_checked:
                await self.selector_strategy.safe_click(locator)
                logger.debug(f"Radio/Checkbox marcado: {field.canonical_key}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error completando radio/checkbox: {e}")
            return False
    
    async def _complete_file(self, locator, field: FormField) -> bool:
        """
        Completa un campo de tipo file (upload).
        
        Args:
            locator: Locator del campo
            field: Metadatos del campo
            
        Returns:
            True si se completó exitosamente
        """
        try:
            # Obtener ruta al PDF de prueba
            pdf_path = Path(self.config.test_pdf_path)
            
            if not pdf_path.exists():
                logger.warning(f"PDF de prueba no encontrado: {pdf_path}")
                return False
            
            # Subir archivo
            await locator.set_input_files(str(pdf_path))
            
            logger.info(f"Archivo subido: {field.canonical_key} = {pdf_path.name}")
            
            # Guardar información del upload
            self.generated_data[field.canonical_key] = str(pdf_path.name)
            
            return True
            
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            return False

