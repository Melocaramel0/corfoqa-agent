"""
Estrategias multi-selector para localización robusta de elementos.
Proporciona heurísticas para encontrar elementos usando múltiples estrategias.
"""

from typing import Optional, List, Dict, Any
from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
import logging

logger = logging.getLogger(__name__)


class SelectorStrategy:
    """Estrategia multi-selector para localizar elementos de forma robusta"""
    
    def __init__(self, page: Page, timeout: int = 10000):
        """
        Inicializa la estrategia de selectores.
        
        Args:
            page: Página de Playwright
            timeout: Timeout por defecto en ms
        """
        self.page = page
        self.timeout = timeout
    
    async def find_element(
        self,
        selectors: List[str],
        visible: bool = True,
        timeout: Optional[int] = None
    ) -> Optional[Locator]:
        """
        Intenta encontrar un elemento usando múltiples selectores.
        
        Args:
            selectors: Lista de selectores CSS/Playwright a intentar
            visible: Si True, solo busca elementos visibles
            timeout: Timeout específico (usa self.timeout si no se provee)
            
        Returns:
            Locator del elemento encontrado o None
        """
        timeout = timeout or self.timeout
        
        for selector in selectors:
            try:
                locator = self.page.locator(selector)
                
                # Verificar visibilidad si se requiere
                if visible:
                    await locator.first.wait_for(state="visible", timeout=timeout)
                else:
                    await locator.first.wait_for(state="attached", timeout=timeout)
                
                # Verificar que el elemento existe
                count = await locator.count()
                if count > 0:
                    logger.debug(f"Elemento encontrado con selector: {selector}")
                    return locator.first
                    
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Error con selector {selector}: {e}")
                continue
        
        logger.warning(f"No se encontró elemento con ninguno de los selectores: {selectors}")
        return None
    
    async def find_by_text(
        self,
        text: str,
        tag: Optional[str] = None,
        exact: bool = False
    ) -> Optional[Locator]:
        """
        Encuentra un elemento por su texto visible.
        
        Args:
            text: Texto a buscar
            tag: Tag HTML específico (opcional)
            exact: Si True, busca match exacto; si False, match parcial
            
        Returns:
            Locator del elemento encontrado o None
        """
        try:
            # Construir selector
            if tag:
                if exact:
                    selector = f'{tag}:text-is("{text}")'
                else:
                    selector = f'{tag}:has-text("{text}")'
            else:
                if exact:
                    selector = f':text-is("{text}")'
                else:
                    selector = f':has-text("{text}")'
            
            locator = self.page.locator(selector)
            await locator.first.wait_for(state="visible", timeout=self.timeout)
            
            count = await locator.count()
            if count > 0:
                logger.debug(f"Elemento encontrado por texto: {text}")
                return locator.first
                
        except PlaywrightTimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Error buscando por texto '{text}': {e}")
        
        return None
    
    async def find_by_label(self, label_text: str) -> Optional[Locator]:
        """
        Encuentra un campo de formulario por su etiqueta (label).
        
        Args:
            label_text: Texto del label
            
        Returns:
            Locator del campo asociado o None
        """
        try:
            # Intenta encontrar el input asociado al label
            locator = self.page.locator(f'label:has-text("{label_text}")').locator('..').locator('input, select, textarea')
            await locator.first.wait_for(state="attached", timeout=self.timeout)
            
            count = await locator.count()
            if count > 0:
                return locator.first
                
            # Alternativa: buscar input con aria-label
            locator = self.page.locator(f'[aria-label="{label_text}"]')
            await locator.first.wait_for(state="attached", timeout=self.timeout)
            
            count = await locator.count()
            if count > 0:
                return locator.first
                
        except PlaywrightTimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Error buscando por label '{label_text}': {e}")
        
        return None
    
    async def find_input_by_placeholder(self, placeholder: str) -> Optional[Locator]:
        """
        Encuentra un campo input por su placeholder.
        
        Args:
            placeholder: Texto del placeholder
            
        Returns:
            Locator del campo o None
        """
        try:
            locator = self.page.locator(f'[placeholder*="{placeholder}"]')
            await locator.first.wait_for(state="attached", timeout=self.timeout)
            
            count = await locator.count()
            if count > 0:
                return locator.first
                
        except PlaywrightTimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Error buscando por placeholder '{placeholder}': {e}")
        
        return None
    
    async def scroll_to_element(self, locator: Locator) -> None:
        """
        Hace scroll hasta un elemento para hacerlo visible.
        
        Args:
            locator: Elemento al que hacer scroll
        """
        try:
            await locator.scroll_into_view_if_needed(timeout=self.timeout)
            logger.debug("Scroll realizado al elemento")
        except Exception as e:
            logger.warning(f"Error al hacer scroll: {e}")
    
    async def safe_click(self, locator: Locator, retries: int = 3) -> bool:
        """
        Hace click de forma segura con reintentos y scroll automático.
        
        Args:
            locator: Elemento a clickear
            retries: Número de reintentos
            
        Returns:
            True si el click fue exitoso
        """
        for attempt in range(retries):
            try:
                # Asegurar que el elemento es visible
                await locator.wait_for(state="visible", timeout=self.timeout)
                
                # Hacer scroll si es necesario
                await self.scroll_to_element(locator)
                
                # Intentar click
                await locator.click(timeout=self.timeout)
                logger.debug(f"Click exitoso en intento {attempt + 1}")
                return True
                
            except PlaywrightTimeoutError:
                if attempt < retries - 1:
                    logger.debug(f"Reintentando click (intento {attempt + 2}/{retries})")
                    await self.page.wait_for_timeout(1000)
                else:
                    logger.error("Click falló después de todos los reintentos")
            except Exception as e:
                logger.error(f"Error en click: {e}")
                if attempt < retries - 1:
                    await self.page.wait_for_timeout(1000)
        
        return False
    
    async def safe_fill(self, locator: Locator, value: str, clear_first: bool = True) -> bool:
        """
        Rellena un campo de forma segura.
        
        Args:
            locator: Campo a rellenar
            value: Valor a ingresar
            clear_first: Si True, limpia el campo primero
            
        Returns:
            True si fue exitoso
        """
        try:
            # Asegurar que el campo es visible
            await locator.wait_for(state="visible", timeout=self.timeout)
            
            # Hacer scroll si es necesario
            await self.scroll_to_element(locator)
            
            # Limpiar campo si se solicita
            if clear_first:
                await locator.clear()
            
            # Rellenar campo
            await locator.fill(value)
            logger.debug(f"Campo rellenado con valor: {value[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error rellenando campo: {e}")
            return False
    
    async def get_all_form_fields(self) -> List[Locator]:
        """
        Obtiene todos los campos de formulario en la página.
        
        Returns:
            Lista de locators de campos de formulario
        """
        fields = []
        
        # Selectores para diferentes tipos de campos
        field_selectors = [
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
            'select',
            'textarea',
            '[role="textbox"]',
            '[role="combobox"]',
            '[contenteditable="true"]',
        ]
        
        for selector in field_selectors:
            try:
                locators = self.page.locator(selector)
                count = await locators.count()
                
                for i in range(count):
                    fields.append(locators.nth(i))
                    
            except Exception as e:
                logger.debug(f"Error obteniendo campos con selector {selector}: {e}")
        
        logger.info(f"Total de campos encontrados: {len(fields)}")
        return fields

