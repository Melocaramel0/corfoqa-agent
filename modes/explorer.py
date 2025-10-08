"""
Modo Explorer: Mapea la estructura completa del formulario.
Descubre pasos, secciones, botones de navegación y mecanismos de progreso.
Sistema robusto que se adapta a formularios dinámicos con diferentes cantidades
de pasos, preguntas y desplegables.
"""

import logging
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, Locator
from datetime import datetime

from utils.selectors import SelectorStrategy
from utils.resilience import NavigationWaiter, LoopDetector
from config import COMMON_SELECTORS

logger = logging.getLogger(__name__)


class FormStep:
    """Representa un paso/sección del formulario (solo estructura, no contenido)"""
    
    def __init__(
        self,
        index: int,
        title: str,
        seccion_id: str,
        url: Optional[str] = None
    ):
        """
        Inicializa un paso del formulario.
        
        Args:
            index: Índice del paso (0-based)
            title: Título o nombre del paso
            seccion_id: ID de la sección (data-seccionid)
            url: URL asociada al paso
        """
        self.index = index
        self.title = title
        self.seccion_id = seccion_id
        self.url = url
        self.collapsibles: List[Dict[str, str]] = []
        self.has_form_content = False
        self.timestamp = datetime.now()
    
    def add_collapsible(self, collapsible_info: Dict[str, str]) -> None:
        """Agrega información de un desplegable encontrado"""
        self.collapsibles.append(collapsible_info)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el paso a diccionario"""
        return {
            "index": self.index,
            "title": self.title,
            "seccion_id": self.seccion_id,
            "url": self.url,
            "has_form_content": self.has_form_content,
            "total_collapsibles": len(self.collapsibles),
            "collapsibles": self.collapsibles,
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
        Ejecuta el modo Explorer: mapea solo la ESTRUCTURA del formulario.
        
        Responsabilidades del Explorer:
        1. Detectar todos los pasos desde la barra de navegación
        2. Para cada paso:
           - Identificar desplegables/acordeones (sin expandirlos)
           - Verificar que tiene contenido de formulario
           - Guardar información estructural
        3. Probar navegación entre pasos
        4. NO extrae valores ni contenido de campos (eso es responsabilidad del Extractor)
        
        Returns:
            Diccionario con el mapa estructural del formulario
        """
        logger.info("=== Iniciando modo Explorer ===")
        logger.info("Objetivo: Mapear estructura del formulario (pasos, desplegables, navegación)")
        logger.info(f"URL actual: {self.page.url}")
        start_time = datetime.now()
        
        try:
            # Paso 1: Detectar todos los pasos desde la barra
            steps_info = await self._detect_steps_from_bar()
            
            if len(steps_info) == 0:
                logger.error("⚠️ NO se detectaron pasos. Verificando contenido de la página...")
                # Debug: verificar qué elementos hay en la página
                try:
                    page_title = await self.page.title()
                    logger.info(f"Título de la página: {page_title}")
                    
                    # Verificar si hay algún formulario
                    forms = await self.page.locator("form").count()
                    logger.info(f"Formularios encontrados: {forms}")
                    
                    # Verificar contenido del body
                    body_text = await self.page.locator("body").text_content()
                    if body_text:
                        logger.info(f"Primeros 200 caracteres del body: {body_text[:200]}")
                except Exception as e:
                    logger.error(f"Error en debug: {e}")
            
            logger.info(f"✓ Detectados {len(steps_info)} pasos en la barra de navegación")
            
            # Paso 2: Recorrer cada paso y mapear su estructura
            for step_info in steps_info:
                logger.info(f"--- Mapeando paso {step_info['index'] + 1}/{len(steps_info)}: {step_info['title']} ---")
                
                # Crear objeto FormStep
                step = FormStep(
                    index=step_info['index'],
                    title=step_info['title'],
                    seccion_id=step_info['seccion_id'],
                    url=self.page.url
                )
                
                # Mapear estructura del paso (sin extraer valores)
                await self._map_step_structure(step)
                
                # Guardar paso
                self.steps.append(step)
                logger.info(f"✓ Paso mapeado: {len(step.collapsibles)} desplegables detectados")
                
                # Navegar al siguiente paso (excepto en el último)
                if step_info['index'] < len(steps_info) - 1:
                    navigated = await self._navigate_to_next_step()
                    if not navigated:
                        logger.warning(f"No se pudo navegar al paso {step_info['index'] + 2}")
                        break
            
            # Paso 3: Recopilar metadatos generales
            await self._collect_metadata()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            total_collapsibles = sum(len(step.collapsibles) for step in self.steps)
            
            logger.info(f"=== Explorer completado en {execution_time:.2f}s ===")
            logger.info(f"Total de pasos mapeados: {len(self.steps)}")
            logger.info(f"Total de desplegables detectados: {total_collapsibles}")
            
            return {
                "success": True,
                "execution_time": execution_time,
                "total_steps": len(self.steps),
                "total_collapsibles": total_collapsibles,
                "steps": [step.to_dict() for step in self.steps],
                "form_metadata": self.form_metadata
            }
            
        except Exception as e:
            logger.error(f"Error en modo Explorer: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "steps": [step.to_dict() for step in self.steps]
            }
    
    async def _detect_steps_from_bar(self) -> List[Dict[str, Any]]:
        """
        Detecta todos los pasos desde la barra de navegación.
        
        Returns:
            Lista de diccionarios con información de cada paso
        """
        steps_info = []
        
        try:
            # Esperar a que aparezca el contenedor de la barra de pasos
            logger.info("Esperando a que aparezca la barra de pasos (#BarraPasosContenedor)...")
            try:
                await self.page.wait_for_selector("#BarraPasosContenedor", state="visible", timeout=10000)
                logger.info("✓ Barra de pasos encontrada")
            except Exception as e:
                logger.warning(f"No se encontró barra de pasos (#BarraPasosContenedor): {e}")
                logger.info(f"URL actual en detección: {self.page.url}")
                return []
            
            # Esperar hasta que existan 'li[id^=BotonPaso_]' bajo la barra (Slick puede inicializarse tarde)
            try:
                await self.page.wait_for_function(
                    "() => !!document.querySelector('#BarraPasosContenedor') && document.querySelectorAll('#BarraPasosContenedor li[id^=\\'BotonPaso_\\']').length > 0",
                    timeout=20000
                )
            except Exception:
                logger.warning("No aparecieron elementos de pasos en el tiempo esperado")
            
            # Buscar li de pasos dentro de la barra (sin depender estrictamente de .slick-track)
            step_items = self.page.locator("#BarraPasosContenedor li[id^='BotonPaso_']")
            step_count = await step_items.count()
            
            if step_count == 0:
                # Fallback: intentar dentro de .slick-track si existe
                bar_track = self.page.locator("#BarraPasosContenedor .slick-track")
                if await bar_track.count() > 0:
                    step_items = bar_track.locator("li[id^='BotonPaso_']")
                    step_count = await step_items.count()
            
            if step_count == 0:
                logger.warning("No se detectaron elementos de pasos (li[id^='BotonPaso_']) bajo #BarraPasosContenedor")
                return []
            
            # Extraer información de cada paso
            for i in range(step_count):
                item = step_items.nth(i)
                
                # Obtener ID de la sección
                span = item.locator("span.glyphicon.BotonPaso")
                seccion_id = await span.get_attribute("data-seccionid")
                
                # Obtener título del paso
                title_span = item.locator("span:not(.glyphicon)")
                title = await title_span.text_content()
                
                # Obtener índice
                index = await item.get_attribute("data-slick-index")
                
                steps_info.append({
                    "index": int(index) if index else i,
                    "title": title.strip() if title else f"Paso {i + 1}",
                    "seccion_id": seccion_id,
                    "element_id": await item.get_attribute("id")
                })
                
                logger.debug(f"Paso detectado: {steps_info[-1]['title']} (ID: {seccion_id})")
            
            # También intentar detectar paso de "Confirmación"
            # Buscar dentro de la barra completa (independiente de .slick-track)
            confirmacion = self.page.locator("#BarraPasosContenedor #PasoConfirmacion")
            if await confirmacion.count() > 0:
                span = confirmacion.locator("span.glyphicon.BotonPaso")
                seccion_id = await span.get_attribute("data-seccionid")
                title_elem = confirmacion.locator("h5#lblConfirmacion")
                title = await title_elem.text_content()
                
                steps_info.append({
                    "index": len(steps_info),
                    "title": title.strip() if title else "Confirmación",
                    "seccion_id": seccion_id,
                    "element_id": "PasoConfirmacion"
                })
                
                logger.debug(f"Paso de confirmación detectado: {steps_info[-1]['title']}")
            
        except Exception as e:
            logger.error(f"Error detectando pasos desde barra: {e}", exc_info=True)
        
        return steps_info
    
    async def _map_step_structure(self, step: FormStep) -> None:
        """
        Mapea la estructura del paso actual (detecta y expande desplegables recursivamente).
        
        Args:
            step: Objeto FormStep donde se almacenará la información estructural
        """
        try:
            # Esperar a que el contenedor esté visible
            await self.page.wait_for_selector("#seccionRender", state="visible", timeout=10000)
            
            # Hacer scroll inicial para cargar todo el contenido
            await self._scroll_to_load_content()
            
            # Detectar y expandir desplegables recursivamente
            collapsibles = await self._detect_and_expand_collapsibles_recursive()
            for collapsible in collapsibles:
                step.add_collapsible(collapsible)
            
            logger.info(f"✓ Detectados {len(collapsibles)} desplegables (incluyendo anidados)")
            
            # Verificar que el paso tiene contenido de formulario
            step.has_form_content = await self._has_form_content()
            
        except Exception as e:
            logger.error(f"Error mapeando estructura del paso: {e}", exc_info=True)
    
    async def _detect_and_expand_collapsibles_recursive(
        self,
        container_selector: str = "#seccionRender",
        nivel: int = 0,
        max_nivel: int = 5,
        parent_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Detecta y expande desplegables de forma recursiva, manejando anidamiento.
        
        Args:
            container_selector: Selector del contenedor donde buscar
            nivel: Nivel actual de anidamiento
            max_nivel: Nivel máximo de anidamiento a explorar
            parent_id: ID del desplegable padre (para tracking)
            
        Returns:
            Lista de todos los desplegables encontrados (incluyendo anidados)
        """
        all_collapsibles = []
        
        if nivel >= max_nivel:
            logger.debug(f"Nivel máximo de anidamiento alcanzado: {nivel}")
            return all_collapsibles
        
        try:
            # Buscar desplegables en el contenedor actual
            collapse_triggers = self.page.locator(f'{container_selector} > div a[data-toggle="collapse"]')
            
            # También buscar en panel-group directamente bajo el contenedor
            panel_group_triggers = self.page.locator(f'{container_selector} > .panel-group a[data-toggle="collapse"]')
            
            # Combinar ambas búsquedas
            all_triggers_selector = f'{container_selector} a[data-toggle="collapse"]'
            all_triggers = self.page.locator(all_triggers_selector)
            count = await all_triggers.count()
            
            if count == 0:
                logger.debug(f"No se encontraron desplegables en nivel {nivel} (contenedor: {container_selector})")
                return all_collapsibles
            
            logger.debug(f"Nivel {nivel}: Encontrados {count} posibles desplegables en {container_selector}")
            
            # Procesar cada desplegable encontrado
            processed_ids = set()
            
            for i in range(count):
                trigger = all_triggers.nth(i)
                
                try:
                    # Verificar que el trigger está visible y es parte del nivel actual
                    if not await trigger.is_visible():
                        continue
                    
                    # Obtener información del desplegable
                    href = await trigger.get_attribute("href")
                    if not href:
                        continue
                    
                    target_id = href.replace("#", "")
                    
                    # Evitar procesar el mismo ID dos veces
                    if target_id in processed_ids:
                        continue
                    
                    # Obtener el data-nivel del panel asociado
                    target = self.page.locator(f"#{target_id}")
                    if await target.count() == 0:
                        continue
                    
                    data_nivel = await target.get_attribute("data-nivel")
                    
                    # Obtener título
                    title_elem = trigger.locator("h3")
                    title = await title_elem.text_content() if await title_elem.count() > 0 else "Sin título"
                    
                    # Detectar estado inicial (abierto/cerrado)
                    is_collapsed = await self._is_collapsible_collapsed(target)
                    was_initially_collapsed = is_collapsed
                    
                    # Expandir si está colapsado
                    if is_collapsed:
                        logger.debug(f"  [{nivel}] Expandiendo: {title.strip()[:50]}")
                        await trigger.click()
                        
                        # Esperar a que se complete la animación
                        await self.page.wait_for_timeout(800)
                        
                        # Verificar que se expandió correctamente
                        await target.wait_for(state="visible", timeout=5000)
                        
                        # Hacer scroll para cargar contenido que pueda estar fuera de vista
                        await self._scroll_to_load_content()
                    else:
                        logger.debug(f"  [{nivel}] Ya expandido: {title.strip()[:50]}")
                    
                    # Registrar el desplegable
                    collapsible_info = {
                        "title": title.strip(),
                        "target_id": target_id,
                        "selector": f'a[data-toggle="collapse"][href="#{target_id}"]',
                        "initially_collapsed": was_initially_collapsed,
                        "nivel": nivel,
                        "data_nivel": data_nivel or f"{nivel}",
                        "parent_id": parent_id
                    }
                    all_collapsibles.append(collapsible_info)
                    processed_ids.add(target_id)
                    
                    # Buscar desplegables anidados dentro de este desplegable
                    # El contenedor hijo será el panel-body del panel-group asociado
                    nested_container = f"#{target_id}"
                    
                    # Buscar panel-group dentro del desplegable expandido
                    panel_group = self.page.locator(f"{nested_container} .panel-group").first
                    if await panel_group.count() > 0:
                        panel_group_id = await panel_group.get_attribute("id")
                        if panel_group_id:
                            nested_container = f"#{panel_group_id}"
                        
                        logger.debug(f"  [{nivel}] Buscando anidados en: {nested_container}")
                        
                        # Recursión para encontrar desplegables anidados
                        nested_collapsibles = await self._detect_and_expand_collapsibles_recursive(
                            container_selector=nested_container,
                            nivel=nivel + 1,
                            max_nivel=max_nivel,
                            parent_id=target_id
                        )
                        
                        all_collapsibles.extend(nested_collapsibles)
                
                except Exception as e:
                    logger.debug(f"Error procesando desplegable {i} en nivel {nivel}: {e}")
                    continue
            
            logger.debug(f"Nivel {nivel}: Total procesados {len(processed_ids)} desplegables únicos")
            
        except Exception as e:
            logger.error(f"Error en detección recursiva (nivel {nivel}): {e}", exc_info=True)
        
        return all_collapsibles
    
    async def _is_collapsible_collapsed(self, target_locator: Locator) -> bool:
        """
        Verifica si un desplegable está colapsado.
        
        Args:
            target_locator: Locator del elemento target del desplegable
            
        Returns:
            True si está colapsado, False si está expandido
        """
        try:
            # Verificar clases comunes para estado expandido
            has_in = await target_locator.evaluate("el => el.classList.contains('in')")
            has_show = await target_locator.evaluate("el => el.classList.contains('show')")
            
            # También verificar el aria-expanded del trigger
            is_visible = await target_locator.is_visible()
            
            # Está colapsado si no tiene 'in' ni 'show' o no es visible
            return not (has_in or has_show or is_visible)
            
        except Exception as e:
            logger.debug(f"Error verificando estado de colapso: {e}")
            return True  # Por defecto, asumir colapsado
    
    async def _scroll_to_load_content(self) -> None:
        """
        Hace scroll en el contenedor #seccionRender para cargar todo el contenido,
        especialmente útil después de expandir desplegables que aumentan la altura.
        """
        try:
            container = self.page.locator("#seccionRender")
            
            if await container.count() == 0:
                logger.debug("Contenedor #seccionRender no encontrado para scroll")
                return
            
            # Hacer scroll al final para asegurar que todo el contenido se carga
            await container.evaluate("el => el.scrollTop = el.scrollHeight")
            await self.page.wait_for_timeout(300)
            
            # Hacer scroll al inicio
            await container.evaluate("el => el.scrollTop = 0")
            await self.page.wait_for_timeout(200)
            
            logger.debug("Scroll completado para cargar contenido")
            
        except Exception as e:
            logger.debug(f"Error en scroll: {e}")
    
    async def _has_form_content(self) -> bool:
        """
        Verifica si el paso actual tiene contenido de formulario.
        
        Returns:
            True si hay campos de formulario, False en caso contrario
        """
        try:
            # Buscar campos con data-controlid
            fields = self.page.locator("#seccionRender [data-controlid]")
            count = await fields.count()
            return count > 0
        except Exception:
            return False
        
    
    async def _navigate_to_next_step(self) -> bool:
        """
        Navega al siguiente paso usando el botón "Siguiente" y maneja
        el modal de confirmación si aparece.
        
        Returns:
            True si logró navegar, False en caso contrario
        """
        try:
            # Buscar botón "Siguiente"
            next_button = self.page.locator("#BotonSig")
            if await next_button.count() == 0:
                logger.warning("No se encontró botón 'Siguiente'")
                return False
            
            if not await next_button.is_visible() or not await next_button.is_enabled():
                logger.warning("Botón 'Siguiente' no visible o deshabilitado")
                return False
            
            logger.debug("Haciendo click en botón 'Siguiente'")
            await next_button.click()
            
            # Si aparece modal de confirmación, aceptar "Sí, estoy seguro"
            try:
                # Esperar breve para que aparezca el modal
                await self.page.wait_for_timeout(500)
                modal_yes_selectors = [
                    "button:has-text('Sí, estoy seguro')",
                    "button:has-text('Si, estoy seguro')",
                    "button:has-text('Sí')",
                    "a.btn-primary:has-text('Sí')"
                ]
                for sel in modal_yes_selectors:
                    btn = self.page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        logger.info("Confirmación detectada, aceptando...")
                        await btn.click()
                        break
            except Exception:
                # Si no aparece modal, continuar normalmente
                pass
            
            # Esperar a que se complete la navegación/cambio de contenido
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await self.page.wait_for_selector("#seccionRender", state="visible", timeout=15000)
            logger.debug("Navegación al siguiente paso completada")
            return True
        except Exception as e:
            logger.error(f"Error navegando al siguiente paso: {e}")
            return False
    
    
    async def _collect_metadata(self) -> None:
        """Recopila metadatos generales del formulario"""
        logger.debug("Recopilando metadatos del formulario...")
        
        self.form_metadata["url"] = self.page.url
        self.form_metadata["total_steps"] = len(self.steps)
        self.form_metadata["structure_type"] = "wizard"
        self.form_metadata["has_step_bar"] = True
        self.form_metadata["step_bar_selector"] = "#BarraPasosContenedor"
        
        # Título de la página
        try:
            self.form_metadata["page_title"] = await self.page.title()
        except Exception:
            self.form_metadata["page_title"] = "N/A"
        
        # Verificar si hay barra de progreso
        try:
            progress_bar = self.page.locator("#BarraPasosContenedor .progress-bar")
            if await progress_bar.count() > 0:
                self.form_metadata["has_progress_bar"] = True
            else:
                self.form_metadata["has_progress_bar"] = False
        except Exception:
            self.form_metadata["has_progress_bar"] = False
        
        logger.debug("Metadatos recopilados")
    
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

