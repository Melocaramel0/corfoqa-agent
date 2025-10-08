"""
Modo Explorer: Mapea la estructura completa del formulario.
Descubre pasos, secciones, botones de navegación y mecanismos de progreso.
"""

import logging
from typing import Optional, List, Dict, Any
from playwright.async_api import Page
from datetime import datetime

from utils.selectors import SelectorStrategy
from utils.resilience import NavigationWaiter, LoopDetector
from config import COMMON_SELECTORS

logger = logging.getLogger(__name__)


class FormStep:
    """Representa un paso/sección del formulario"""
    
    def __init__(
        self,
        index: int,
        title: Optional[str] = None,
        url: Optional[str] = None,
        selector: Optional[str] = None
    ):
        """
        Inicializa un paso del formulario.
        
        Args:
            index: Índice del paso (0-based)
            title: Título o nombre del paso
            url: URL asociada al paso
            selector: Selector CSS del contenedor del paso
        """
        self.index = index
        self.title = title or f"Paso {index + 1}"
        self.url = url
        self.selector = selector
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el paso a diccionario"""
        return {
            "index": self.index,
            "title": self.title,
            "url": self.url,
            "selector": self.selector,
            "timestamp": self.timestamp.isoformat()
        }


class Explorer:
    """Modo Explorer: Descubre y mapea la estructura del formulario"""
    
    def __init__(self, page: Page, config):
        """
        Inicializa el explorador.
        
        Args:
            page: Página de Playwright
            config: Configuración del agente
        """
        self.page = page
        self.config = config
        self.selector_strategy = SelectorStrategy(page, config.timeout_element)
        self.nav_waiter = NavigationWaiter(page)
        self.loop_detector = LoopDetector(max_same_state=3)
        
        # Resultados del mapeo
        self.steps: List[FormStep] = []
        self.navigation_buttons: Dict[str, List[str]] = {
            "next": [],
            "previous": [],
            "submit": []
        }
        self.form_metadata: Dict[str, Any] = {}
    
    async def explore(self) -> Dict[str, Any]:
        """
        Ejecuta el modo Explorer completo.
        
        Returns:
            Diccionario con toda la información descubierta
        """
        logger.info("=== Iniciando modo Explorer ===")
        start_time = datetime.now()
        
        try:
            # Paso 1: Identificar estructura general del formulario
            await self._identify_form_structure()
            
            # Paso 2: Detectar mecanismo de navegación
            await self._detect_navigation_mechanism()
            
            # Paso 3: Mapear todos los pasos del formulario
            await self._map_all_steps()
            
            # Paso 4: Recopilar metadatos generales
            await self._collect_metadata()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Explorer completado en {execution_time:.2f}s")
            logger.info(f"Total de pasos descubiertos: {len(self.steps)}")
            
            return {
                "success": True,
                "execution_time": execution_time,
                "total_steps": len(self.steps),
                "steps": [step.to_dict() for step in self.steps],
                "navigation_buttons": self.navigation_buttons,
                "form_metadata": self.form_metadata
            }
            
        except Exception as e:
            logger.error(f"Error en modo Explorer: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "steps": [step.to_dict() for step in self.steps]
            }
    
    async def _identify_form_structure(self) -> None:
        """Identifica la estructura general del formulario (wizard, tabs, single-page, etc.)"""
        logger.info("Identificando estructura del formulario...")
        
        # Buscar indicadores de estructura tipo wizard
        wizard_indicators = [
            '.wizard', '.stepper', '.step-container', '[role="tablist"]',
            '.form-wizard', '.multi-step-form', '.progress-steps'
        ]
        
        for selector in wizard_indicators:
            try:
                locator = self.page.locator(selector)
                count = await locator.count()
                
                if count > 0:
                    self.form_metadata["structure_type"] = "wizard"
                    self.form_metadata["wizard_selector"] = selector
                    logger.info(f"Estructura tipo wizard detectada: {selector}")
                    return
            except Exception:
                continue
        
        # Buscar tabs
        tab_selectors = ['[role="tab"]', '.tab', '.nav-tabs']
        for selector in tab_selectors:
            try:
                locator = self.page.locator(selector)
                count = await locator.count()
                
                if count > 1:  # Al menos 2 tabs
                    self.form_metadata["structure_type"] = "tabs"
                    self.form_metadata["tab_selector"] = selector
                    logger.info(f"Estructura tipo tabs detectada: {selector}")
                    return
            except Exception:
                continue
        
        # Por defecto: single-page o wizard simple
        self.form_metadata["structure_type"] = "single-page"
        logger.info("Estructura de página única o wizard simple")
    
    async def _detect_navigation_mechanism(self) -> None:
        """Detecta los botones y mecanismos de navegación entre pasos"""
        logger.info("Detectando mecanismo de navegación...")
        
        # Buscar botón "Siguiente"
        next_button = await self.selector_strategy.find_element(
            COMMON_SELECTORS["next_button"],
            visible=False
        )
        
        if next_button:
            # Obtener selector usado
            for selector in COMMON_SELECTORS["next_button"]:
                try:
                    loc = self.page.locator(selector)
                    count = await loc.count()
                    if count > 0:
                        self.navigation_buttons["next"].append(selector)
                        logger.info(f"Botón 'Siguiente' encontrado: {selector}")
                        break
                except Exception:
                    continue
        
        # Buscar botón "Anterior"
        prev_button = await self.selector_strategy.find_element(
            COMMON_SELECTORS["previous_button"],
            visible=False
        )
        
        if prev_button:
            for selector in COMMON_SELECTORS["previous_button"]:
                try:
                    loc = self.page.locator(selector)
                    count = await loc.count()
                    if count > 0:
                        self.navigation_buttons["previous"].append(selector)
                        logger.info(f"Botón 'Anterior' encontrado: {selector}")
                        break
                except Exception:
                    continue
        
        # Buscar botón "Enviar/Finalizar"
        submit_button = await self.selector_strategy.find_element(
            COMMON_SELECTORS["submit_button"],
            visible=False
        )
        
        if submit_button:
            for selector in COMMON_SELECTORS["submit_button"]:
                try:
                    loc = self.page.locator(selector)
                    count = await loc.count()
                    if count > 0:
                        self.navigation_buttons["submit"].append(selector)
                        logger.info(f"Botón 'Enviar' encontrado: {selector}")
                        break
                except Exception:
                    continue
    
    async def _map_all_steps(self) -> None:
        """Mapea todos los pasos del formulario navegando por ellos"""
        logger.info("Mapeando todos los pasos del formulario...")
        
        current_step = 0
        max_steps = 30  # Límite de seguridad
        
        while current_step < max_steps:
            # Registrar paso actual
            url = self.page.url
            
            # Intentar obtener título del paso
            title = await self._get_step_title()
            
            # Crear y guardar el paso
            step = FormStep(
                index=current_step,
                title=title,
                url=url
            )
            self.steps.append(step)
            logger.info(f"Paso {current_step + 1} mapeado: {title}")
            
            # Detectar bucle
            state_key = f"{url}_{title}_{current_step}"
            if self.loop_detector.record_state(state_key):
                logger.warning("Bucle detectado en navegación de pasos")
                break
            
            # Intentar avanzar al siguiente paso
            advanced = await self._advance_to_next_step()
            
            if not advanced:
                # No hay más pasos
                logger.info("No se puede avanzar más, fin del formulario alcanzado")
                break
            
            # Esperar a que la página se estabilice
            await self.nav_waiter.wait_for_navigation_complete(
                timeout=self.config.timeout_navigation
            )
            
            current_step += 1
        
        logger.info(f"Mapeo completado: {len(self.steps)} pasos encontrados")
    
    async def _get_step_title(self) -> str:
        """
        Intenta obtener el título del paso actual.
        
        Returns:
            Título del paso o título por defecto
        """
        # Intentar con diferentes selectores comunes
        title_selectors = [
            'h1', 'h2', 'h3',
            '.step-title', '.wizard-title', '.form-title',
            '[role="heading"]', '.section-title'
        ]
        
        for selector in title_selectors:
            try:
                locator = self.page.locator(selector).first
                text = await locator.text_content(timeout=2000)
                
                if text and len(text.strip()) > 0:
                    return text.strip()
            except Exception:
                continue
        
        # Si no se encuentra título, usar título de la página
        try:
            title = await self.page.title()
            if title:
                return title
        except Exception:
            pass
        
        return f"Paso {len(self.steps) + 1}"
    
    async def _advance_to_next_step(self) -> bool:
        """
        Intenta avanzar al siguiente paso.
        
        Returns:
            True si logró avanzar, False si no hay más pasos
        """
        # Buscar botón "Siguiente"
        if self.navigation_buttons["next"]:
            # Usar el selector conocido
            for selector in self.navigation_buttons["next"]:
                next_button = self.page.locator(selector).first
                
                try:
                    # Verificar si el botón está visible y habilitado
                    is_visible = await next_button.is_visible(timeout=2000)
                    is_enabled = await next_button.is_enabled()
                    
                    if is_visible and is_enabled:
                        # Guardar URL actual para detectar cambio
                        current_url = self.page.url
                        
                        # Click en el botón
                        await self.selector_strategy.safe_click(next_button)
                        
                        # Esperar cambio
                        await self.page.wait_for_timeout(1000)
                        
                        # Verificar si cambió algo (URL o contenido)
                        new_url = self.page.url
                        if new_url != current_url:
                            logger.debug("URL cambió, paso avanzado")
                            return True
                        
                        # Si la URL no cambió, verificar cambio de contenido
                        # (formularios tipo wizard en la misma URL)
                        return True
                        
                except Exception as e:
                    logger.debug(f"Error intentando avanzar con {selector}: {e}")
                    continue
        
        # Buscar botón "Enviar" (último paso)
        if self.navigation_buttons["submit"]:
            for selector in self.navigation_buttons["submit"]:
                try:
                    submit_button = self.page.locator(selector).first
                    is_visible = await submit_button.is_visible(timeout=2000)
                    
                    if is_visible:
                        logger.info("Botón de envío encontrado, último paso alcanzado")
                        return False
                except Exception:
                    continue
        
        logger.debug("No se encontró botón de navegación")
        return False
    
    async def _collect_metadata(self) -> None:
        """Recopila metadatos generales del formulario"""
        logger.info("Recopilando metadatos del formulario...")
        
        self.form_metadata["url"] = self.page.url
        self.form_metadata["total_steps"] = len(self.steps)
        
        # Título de la página
        try:
            self.form_metadata["page_title"] = await self.page.title()
        except Exception:
            self.form_metadata["page_title"] = "N/A"
        
        # Detectar si hay barra de progreso
        progress_selectors = [
            '[role="progressbar"]', '.progress', '.progress-bar',
            '.step-progress', '.wizard-progress'
        ]
        
        for selector in progress_selectors:
            try:
                locator = self.page.locator(selector)
                count = await locator.count()
                
                if count > 0:
                    self.form_metadata["has_progress_bar"] = True
                    self.form_metadata["progress_selector"] = selector
                    break
            except Exception:
                continue
        else:
            self.form_metadata["has_progress_bar"] = False
        
        logger.info("Metadatos recopilados")
    
    async def navigate_to_step(self, step_index: int) -> bool:
        """
        Navega a un paso específico.
        
        Args:
            step_index: Índice del paso (0-based)
            
        Returns:
            True si logró navegar al paso
        """
        if step_index >= len(self.steps):
            logger.error(f"Paso {step_index} fuera de rango")
            return False
        
        target_step = self.steps[step_index]
        
        # Intentar navegar directamente por URL si está disponible
        if target_step.url and target_step.url != self.page.url:
            try:
                await self.page.goto(target_step.url)
                await self.nav_waiter.wait_for_navigation_complete()
                logger.info(f"Navegado a paso {step_index} por URL")
                return True
            except Exception as e:
                logger.debug(f"No se pudo navegar por URL: {e}")
        
        # TODO: Implementar navegación por clicks si es necesario
        logger.warning("Navegación directa a pasos aún no implementada completamente")
        return False

