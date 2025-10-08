"""
Heurísticas de resiliencia y recuperación ante fallos.
Maneja reintentos, timeouts, detección de bucles y recuperación de errores.
"""

import asyncio
import logging
from typing import Callable, Any, Optional, TypeVar, Dict
from datetime import datetime, timedelta
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy:
    """Estrategia de reintentos con backoff exponencial"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ):
        """
        Inicializa la estrategia de reintentos.
        
        Args:
            max_retries: Número máximo de reintentos
            base_delay: Delay base en segundos
            max_delay: Delay máximo en segundos
            exponential_base: Base para backoff exponencial
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """
        Calcula el delay para un intento específico.
        
        Args:
            attempt: Número de intento (0-indexed)
            
        Returns:
            Delay en segundos
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    async def execute(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        Ejecuta una función con reintentos.
        
        Args:
            func: Función async a ejecutar
            *args: Argumentos posicionales para la función
            **kwargs: Argumentos nombrados para la función
            
        Returns:
            Resultado de la función o None si falla todos los intentos
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Intentar ejecutar la función
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Operación exitosa en intento {attempt + 1}/{self.max_retries + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    logger.warning(
                        f"Intento {attempt + 1}/{self.max_retries + 1} falló: {str(e)}. "
                        f"Reintentando en {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operación falló después de {self.max_retries + 1} intentos")
        
        # Si llegamos aquí, todos los intentos fallaron
        if last_exception:
            logger.error(f"Último error: {str(last_exception)}")
        
        return None


class LoopDetector:
    """Detector de bucles infinitos en navegación"""
    
    def __init__(self, max_same_state: int = 3, state_ttl: int = 300):
        """
        Inicializa el detector de bucles.
        
        Args:
            max_same_state: Máximo número de veces que se puede repetir un estado
            state_ttl: Tiempo de vida del estado en segundos
        """
        self.max_same_state = max_same_state
        self.state_ttl = timedelta(seconds=state_ttl)
        self.state_history: Dict[str, list] = {}
    
    def record_state(self, state_key: str) -> bool:
        """
        Registra un estado y detecta si estamos en un bucle.
        
        Args:
            state_key: Identificador único del estado (ej: URL + paso actual)
            
        Returns:
            True si se detecta un bucle (estado repetido demasiadas veces)
        """
        now = datetime.now()
        
        # Inicializar historial para este estado si no existe
        if state_key not in self.state_history:
            self.state_history[state_key] = []
        
        # Limpiar entradas antiguas
        self.state_history[state_key] = [
            ts for ts in self.state_history[state_key]
            if now - ts < self.state_ttl
        ]
        
        # Registrar nueva entrada
        self.state_history[state_key].append(now)
        
        # Verificar si excedemos el límite
        count = len(self.state_history[state_key])
        if count >= self.max_same_state:
            logger.error(f"Bucle detectado: estado '{state_key}' repetido {count} veces")
            return True
        
        return False
    
    def clear(self) -> None:
        """Limpia el historial de estados"""
        self.state_history.clear()


class NavigationWaiter:
    """Maneja esperas inteligentes durante la navegación"""
    
    def __init__(self, page: Page):
        """
        Inicializa el waiter de navegación.
        
        Args:
            page: Página de Playwright
        """
        self.page = page
    
    async def wait_for_navigation_complete(
        self,
        timeout: int = 30000,
        wait_for_network_idle: bool = True
    ) -> bool:
        """
        Espera a que la navegación se complete.
        
        Args:
            timeout: Timeout en milisegundos
            wait_for_network_idle: Si True, espera a networkidle
            
        Returns:
            True si la navegación se completó exitosamente
        """
        try:
            # Esperar a que el estado de carga sea 'networkidle' o 'load'
            if wait_for_network_idle:
                await self.page.wait_for_load_state("networkidle", timeout=timeout)
            else:
                await self.page.wait_for_load_state("load", timeout=timeout)
            
            logger.debug("Navegación completada")
            return True
            
        except PlaywrightTimeoutError:
            logger.warning("Timeout esperando navegación")
            return False
        except Exception as e:
            logger.error(f"Error esperando navegación: {e}")
            return False
    
    async def wait_for_element_stable(
        self,
        selector: str,
        timeout: int = 10000,
        stability_time: int = 1000
    ) -> bool:
        """
        Espera a que un elemento sea visible y estable (no se mueva).
        
        Args:
            selector: Selector del elemento
            timeout: Timeout total en milisegundos
            stability_time: Tiempo que el elemento debe permanecer estable en ms
            
        Returns:
            True si el elemento es estable
        """
        try:
            # Esperar a que el elemento sea visible
            locator = self.page.locator(selector)
            await locator.first.wait_for(state="visible", timeout=timeout)
            
            # Esperar un tiempo para que se estabilice
            await self.page.wait_for_timeout(stability_time)
            
            # Verificar que sigue visible
            is_visible = await locator.first.is_visible()
            if is_visible:
                logger.debug(f"Elemento estable: {selector}")
                return True
            
        except Exception as e:
            logger.debug(f"Elemento no estable: {e}")
        
        return False
    
    async def wait_for_any_element(
        self,
        selectors: list[str],
        timeout: int = 10000
    ) -> Optional[str]:
        """
        Espera a que aparezca cualquiera de los selectores dados.
        
        Args:
            selectors: Lista de selectores a esperar
            timeout: Timeout en milisegundos
            
        Returns:
            El selector que apareció primero, o None si ninguno aparece
        """
        start_time = datetime.now()
        timeout_delta = timedelta(milliseconds=timeout)
        
        while datetime.now() - start_time < timeout_delta:
            for selector in selectors:
                try:
                    locator = self.page.locator(selector)
                    count = await locator.count()
                    
                    if count > 0:
                        is_visible = await locator.first.is_visible()
                        if is_visible:
                            logger.debug(f"Elemento encontrado: {selector}")
                            return selector
                            
                except Exception:
                    continue
            
            # Pequeña espera antes de reintentar
            await self.page.wait_for_timeout(500)
        
        logger.warning("Ninguno de los elementos apareció")
        return None
    
    async def wait_for_spinner_gone(
        self,
        spinner_selectors: Optional[list[str]] = None,
        timeout: int = 30000
    ) -> bool:
        """
        Espera a que desaparezcan los spinners/loaders.
        
        Args:
            spinner_selectors: Lista de selectores de spinners (usa defaults si None)
            timeout: Timeout en milisegundos
            
        Returns:
            True si los spinners desaparecieron
        """
        if spinner_selectors is None:
            # Selectores comunes de spinners/loaders
            spinner_selectors = [
                '.spinner',
                '.loader',
                '.loading',
                '[role="progressbar"]',
                '.fa-spinner',
                '.loading-overlay',
            ]
        
        try:
            for selector in spinner_selectors:
                locator = self.page.locator(selector)
                count = await locator.count()
                
                if count > 0:
                    # Esperar a que desaparezca
                    await locator.first.wait_for(state="hidden", timeout=timeout)
                    logger.debug(f"Spinner desapareció: {selector}")
            
            return True
            
        except PlaywrightTimeoutError:
            logger.warning("Timeout esperando que desaparezca spinner")
            return False
        except Exception as e:
            logger.debug(f"Error esperando spinner: {e}")
            return True  # Asumir que no hay spinner si hay error


async def safe_execute(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    log_error: bool = True,
    **kwargs
) -> Optional[T]:
    """
    Ejecuta una función de forma segura capturando excepciones.
    
    Args:
        func: Función async a ejecutar
        *args: Argumentos posicionales
        default: Valor por defecto si falla
        log_error: Si True, loguea errores
        **kwargs: Argumentos nombrados
        
    Returns:
        Resultado de la función o default si falla
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"Error en {func.__name__}: {str(e)}")
        return default

