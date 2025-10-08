"""
Agente de Validación de Formularios Web - Punto de entrada principal.
Orquesta todos los modos de operación: Explorer, Extractor, Completer, Validator, Matcher y Reporter.
"""

import asyncio
import logging
import sys
import argparse
from datetime import datetime
from pathlib import Path

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

from config import Config, AgentMode
from modes.explorer import Explorer
from modes.extractor import Extractor
from modes.completer import Completer
from modes.validator import Validator
from modes.matcher import Matcher
from reporter import Reporter

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('agent.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class FormValidationAgent:
    """Agente principal de validación de formularios"""
    
    def __init__(self, config: Config):
        """
        Inicializa el agente.
        
        Args:
            config: Configuración del agente
        """
        self.config = config
        self.results = {}
        self.execution_start = None
        self.execution_end = None
    
    async def run(self) -> dict:
        """
        Ejecuta el agente según el modo configurado.
        
        Returns:
            Diccionario con todos los resultados
        """
        logger.info("=" * 80)
        logger.info("AGENTE DE VALIDACIÓN DE FORMULARIOS WEB")
        logger.info("=" * 80)
        logger.info(f"Modo: {self.config.mode}")
        logger.info(f"URL: {self.config.form_url}")
        logger.info(f"Headless: {self.config.headless}")
        logger.info("=" * 80)
        
        self.execution_start = datetime.now()
        
        # Asegurar que existen los directorios de salida
        self.config.ensure_directories()
        
        # Crear crawler de Crawlee
        crawler = PlaywrightCrawler(
            headless=self.config.headless,
            browser_type=self.config.browser_type,
            max_request_retries=self.config.max_retries,
        )
        
        # Definir el handler de requests
        @crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            """Handler principal del crawler"""
            page = context.page
            
            # Configurar viewport
            await page.set_viewport_size({
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            })
            
            logger.info(f"Página cargada: {page.url}")
            
            # Detectar y ejecutar login si es necesario
            await self._detect_and_perform_login(page)
            
            # Verificar si necesitamos hacer click en "Nueva Postulación" después del login
            await self._handle_nueva_postulacion_page(page)
            
            # Ejecutar modos según configuración
            if self.config.mode == "full":
                await self._run_full_flow(page)
            elif self.config.mode == "explore":
                await self._run_explore_mode(page)
            elif self.config.mode == "extract":
                await self._run_extract_mode(page)
            elif self.config.mode == "complete":
                await self._run_complete_mode(page)
            elif self.config.mode == "validate":
                await self._run_validate_mode(page)
            elif self.config.mode == "match":
                await self._run_match_mode(page)
            else:
                logger.error(f"Modo desconocido: {self.config.mode}")
        
        # Ejecutar el crawler
        try:
            # Siempre empezar desde la URL del formulario
            # El sistema detectará automáticamente si necesita login
            logger.info(f"URL inicial: {self.config.form_url}")
            await crawler.run([self.config.form_url])
            
            self.execution_end = datetime.now()
            
            # Generar informe final
            reporter = Reporter(self.config)
            report_result = await reporter.generate_report(
                explorer_result=self.results.get("explorer"),
                extractor_result=self.results.get("extractor"),
                completer_result=self.results.get("completer"),
                validator_result=self.results.get("validator"),
                matcher_result=self.results.get("matcher"),
                execution_start=self.execution_start,
                execution_end=self.execution_end
            )
            
            self.results["report"] = report_result
            
            # Mostrar resumen
            self._print_summary()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error ejecutando agente: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _detect_and_perform_login(self, page):
        """
        Detecta automáticamente si la página requiere login y lo ejecuta si es necesario.
        
        Args:
            page: Página de Playwright
        """
        # Si no hay credenciales, no intentar login
        if not self.config.test_username or not self.config.test_password:
            logger.info("No se proporcionaron credenciales, continuando sin login")
            return
        
        try:
            # Esperar a que la página cargue completamente con timeout más largo
            logger.info("Esperando carga completa de la página...")
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)  # Dar tiempo para que se renderice
            
            # Detectar si estamos en una página que requiere login
            # Buscar indicadores de que necesitamos hacer login
            login_indicators = [
                "input[type='password']",  # Campo de contraseña (más genérico)
                "#pass",  # Campo password específico de CORFO
                "#rut",  # Campo RUT específico de CORFO
                "input[name='username']",
                "input[name='user']",
                "text=Iniciar sesión",
                "text=Login",
            ]
            
            needs_login = False
            detected_indicator = None
            for indicator in login_indicators:
                try:
                    element = page.locator(indicator).first
                    is_visible = await element.is_visible(timeout=2000)
                    if is_visible:
                        needs_login = True
                        detected_indicator = indicator
                        logger.info(f"✓ Detectado indicador de login: {indicator}")
                        break
                except:
                    continue
            
            if not needs_login:
                logger.info("No se detectó necesidad de login, continuando sin autenticación...")
                return
            
            logger.info(f"Se detectó necesidad de login (indicador: {detected_indicator}), procediendo con autenticación...")
            await self._perform_corfo_login(page)
            
        except Exception as e:
            logger.warning(f"Error detectando login: {e}")
            logger.info("Continuando sin login debido al error en detección...")
            return
    
    async def _perform_corfo_login(self, page):
        """
        Realiza login específico para el sistema CORFO.
        Detecta automáticamente si ya está en la página de login o necesita navegar.
        
        Args:
            page: Página de Playwright
        """
        logger.info("Realizando login en CORFO...")
        
        try:
            # Verificar si necesitamos hacer click en el link de login primero
            try:
                logger.info("Verificando si existe link de inicio de sesión...")
                login_link = page.locator("#mostrarCorfoLoginLink")
                if await login_link.is_visible(timeout=3000):
                    logger.info("Paso 1: Haciendo click en link de inicio de sesión...")
                    await login_link.click()
                    await page.wait_for_timeout(2000)
                    logger.info("✓ Click en link de inicio de sesión realizado")
            except:
                logger.info("No se encontró link de login, asumiendo que ya estamos en página de login")
            
            # Buscar campos de login con selectores flexibles
            logger.info("Buscando campos de login...")
            
            # Intentar encontrar campo de RUT/Usuario con más selectores
            rut_selectors = [
                "#rut", 
                "input[name='rut']", 
                "input[name='username']",
                "input[name='user']",
                "input[type='text']",
                "input[placeholder*='RUT']",
                "input[placeholder*='Usuario']",
                "input[id*='rut']",
                "input[id*='user']"
            ]
            rut_field = None
            for selector in rut_selectors:
                try:
                    field = page.locator(selector).first
                    if await field.is_visible(timeout=2000):
                        rut_field = field
                        logger.info(f"✓ Campo RUT encontrado: {selector}")
                        break
                except:
                    continue
            
            if not rut_field:
                raise Exception("No se encontró campo de RUT/Usuario")
            
            # Ingresar RUT
            logger.info("Ingresando RUT...")
            await rut_field.fill(self.config.test_username)
            await page.wait_for_timeout(500)
            logger.info(f"✓ RUT ingresado: {self.config.test_username}")
            
            # Intentar encontrar campo de contraseña
            password_selectors = ["#pass", "input[name='password']", "input[type='password']"]
            password_field = None
            for selector in password_selectors:
                try:
                    field = page.locator(selector).first
                    if await field.is_visible(timeout=2000):
                        password_field = field
                        logger.info(f"✓ Campo contraseña encontrado: {selector}")
                        break
                except:
                    continue
            
            if not password_field:
                raise Exception("No se encontró campo de contraseña")
            
            # Ingresar contraseña
            logger.info("Ingresando contraseña...")
            await password_field.fill(self.config.test_password)
            await page.wait_for_timeout(500)
            logger.info("✓ Contraseña ingresada")
            
            # Buscar botón de submit
            submit_selectors = [
                "#ingresa_",
                "input[type='submit']",
                "button[type='submit']",
                "input[value*='Ingresar']",
                "input[value*='Enviar']",
                "button:has-text('Ingresar')",
                "button:has-text('Enviar')"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        submit_button = button
                        logger.info(f"✓ Botón submit encontrado: {selector}")
                        break
                except:
                    continue
            
            if not submit_button:
                raise Exception("No se encontró botón de submit")
            
            # Click en submit
            logger.info("Haciendo click en botón de login...")
            await submit_button.click()
            logger.info("✓ Click en botón realizado")
            
            # Esperar a que cargue la siguiente página con más tiempo
            logger.info("Esperando respuesta del servidor...")
            await page.wait_for_load_state("networkidle", timeout=45000)
            await page.wait_for_timeout(5000)  # Dar más tiempo para que se renderice completamente
            logger.info("✓ Página post-login cargada")
            
            # Verificar si estamos en la página de "Nueva Postulación" y hacer click
            await self._handle_nueva_postulacion_page(page)
            
            logger.info("✓ Login completado exitosamente")
            
        except Exception as e:
            logger.error(f"✗ Error en login: {e}", exc_info=True)
            raise
    
    async def _handle_nueva_postulacion_page(self, page):
        """
        Detecta si estamos en la página de "Nueva Postulación" y hace click si es necesario.
        
        Args:
            page: Página de Playwright
        """
        try:
            logger.info("Verificando si estamos en página de 'Nueva Postulación'...")
            logger.info(f"URL actual: {page.url}")
            
            # Verificar si estamos en la URL específica de postulaciones CORFO
            if "postulador.corfo.cl" in page.url and "PostuladorBorradores.aspx" in page.url:
                logger.info("✓ Detectada URL específica de postulaciones CORFO")
                await self._wait_for_dynamic_content_and_click_nueva_postulacion(page)
                return
            
            # Buscar indicadores de que estamos en la página de postulaciones
            postulacion_indicators = [
                "text=NUEVA POSTULACIÓN",
                "text=Nueva Postulación", 
                "text=Perfil Impulsa",
                "text=Impulsa Transición",
                "text=Borrador",
                "text=Mostrar registros",
                "text=Estado",
                "text=N° Identificador",
                "table",  # Tabla de postulaciones
                "span.btn.btn-primary.btn-xs:has-text('Nueva Postulación')",
                "button:has-text('NUEVA POSTULACIÓN')",
                "a:has-text('NUEVA POSTULACIÓN')"
            ]
            
            is_postulacion_page = False
            for indicator in postulacion_indicators:
                try:
                    element = page.locator(indicator).first
                    if await element.is_visible(timeout=5000):  # Más tiempo para detectar
                        is_postulacion_page = True
                        logger.info(f"✓ Detectada página de postulaciones: {indicator}")
                        break
                except:
                    continue
            
            if not is_postulacion_page:
                logger.info("No se detectó página de postulaciones, continuando...")
                return
            
            # Buscar botón "Nueva Postulación" con múltiples selectores
            nueva_postulacion_selectors = [
                "span.btn.btn-primary.btn-xs:has-text('Nueva Postulación')",
                "button:has-text('NUEVA POSTULACIÓN')",
                "button:has-text('Nueva Postulación')",
                "a:has-text('NUEVA POSTULACIÓN')",
                "a:has-text('Nueva Postulación')",
                "input[value*='Nueva Postulación']",
                "input[value*='NUEVA POSTULACIÓN']"
            ]
            
            nueva_postulacion_button = None
            for selector in nueva_postulacion_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        nueva_postulacion_button = button
                        logger.info(f"✓ Botón 'Nueva Postulación' encontrado: {selector}")
                        break
                except:
                    continue
            
            if nueva_postulacion_button:
                logger.info("Haciendo click en 'Nueva Postulación'...")
                await nueva_postulacion_button.click()
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                logger.info("✓ Click en 'Nueva Postulación' realizado - Accediendo al formulario...")
            else:
                logger.warning("No se encontró botón 'Nueva Postulación' en la página")
                
        except Exception as e:
            logger.warning(f"Error manejando página de postulaciones: {e}")
            # No lanzar excepción, continuar con el flujo normal
    
    async def _wait_for_dynamic_content_and_click_nueva_postulacion(self, page):
        """
        Espera a que se cargue el contenido dinámico de la página de postulaciones CORFO
        y hace click en "Nueva Postulación".
        
        Args:
            page: Página de Playwright
        """
        try:
            logger.info("Esperando a que se cargue el contenido dinámico...")
            
            # Esperar a que desaparezcan los indicadores de carga
            loading_indicators = [
                "text=Consultando...",
                "text=Cargando...",
                "text=Recuperar Clave"
            ]
            
            for indicator in loading_indicators:
                try:
                    element = page.locator(indicator).first
                    if await element.is_visible(timeout=2000):
                        logger.info(f"Esperando a que desaparezca: {indicator}")
                        await element.wait_for(state="hidden", timeout=30000)
                        logger.info(f"✓ {indicator} desapareció")
                except:
                    continue
            
            # Esperar tiempo adicional para que se renderice el contenido
            await page.wait_for_timeout(3000)
            
            # Buscar el botón "Nueva Postulación" con múltiples intentos
            nueva_postulacion_selectors = [
                "span.btn.btn-primary.btn-xs:has-text('Nueva Postulación')",
                "button:has-text('NUEVA POSTULACIÓN')",
                "button:has-text('Nueva Postulación')",
                "a:has-text('NUEVA POSTULACIÓN')",
                "a:has-text('Nueva Postulación')",
                "input[value*='Nueva Postulación']",
                "input[value*='NUEVA POSTULACIÓN']",
                "[class*='btn']:has-text('Nueva Postulación')",
                "[class*='btn']:has-text('NUEVA POSTULACIÓN')"
            ]
            
            # Intentar múltiples veces con diferentes timeouts
            for attempt in range(3):
                logger.info(f"Intento {attempt + 1}/3 de buscar botón 'Nueva Postulación'...")
                
                for selector in nueva_postulacion_selectors:
                    try:
                        button = page.locator(selector).first
                        if await button.is_visible(timeout=5000):
                            logger.info(f"✓ Botón 'Nueva Postulación' encontrado: {selector}")
                            await button.click()
                            await page.wait_for_load_state("domcontentloaded", timeout=30000)
                            await page.wait_for_timeout(3000)
                            logger.info("✓ Click en 'Nueva Postulación' realizado - Accediendo al formulario...")
                            return
                    except:
                        continue
                
                if attempt < 2:  # No es el último intento
                    logger.info("No se encontró el botón, esperando más tiempo...")
                    await page.wait_for_timeout(5000)
            
            logger.warning("No se pudo encontrar el botón 'Nueva Postulación' después de múltiples intentos")
            
        except Exception as e:
            logger.warning(f"Error esperando contenido dinámico: {e}")
    
    async def _run_full_flow(self, page):
        """
        Ejecuta el flujo completo: todos los modos en secuencia.
        
        Args:
            page: Página de Playwright
        """
        logger.info("Ejecutando flujo completo...")
        
        # 1. Explorer
        explorer = Explorer(page, self.config)
        self.results["explorer"] = await explorer.explore()
        
        # 2. Extractor
        extractor = Extractor(page, self.config, self.results["explorer"])
        self.results["extractor"] = await extractor.extract()
        
        # 3. Completer
        if self.results["extractor"].get("success"):
            fields = [
                type('Field', (), field)()  # Crear objetos desde dicts
                for field in self.results["extractor"]["fields"]
            ]
            
            # Reconstruir objetos FormField
            from modes.extractor import FormField
            field_objects = []
            for field_dict in self.results["extractor"]["fields"]:
                field_obj = FormField()
                for key, value in field_dict.items():
                    setattr(field_obj, key, value)
                field_objects.append(field_obj)
            
            completer = Completer(page, self.config, field_objects)
            self.results["completer"] = await completer.complete()
        
        # 4. Validator
        if self.results["extractor"].get("success"):
            from modes.extractor import FormField
            field_objects = []
            for field_dict in self.results["extractor"]["fields"]:
                field_obj = FormField()
                for key, value in field_dict.items():
                    setattr(field_obj, key, value)
                field_objects.append(field_obj)
            
            validator = Validator(page, self.config, field_objects)
            self.results["validator"] = await validator.validate()
        
        # 5. Matcher QA
        if self.results["extractor"].get("success") and self.results["validator"].get("success"):
            from modes.extractor import FormField
            field_objects = []
            for field_dict in self.results["extractor"]["fields"]:
                field_obj = FormField()
                for key, value in field_dict.items():
                    setattr(field_obj, key, value)
                field_objects.append(field_obj)
            
            matcher = Matcher(
                self.config,
                field_objects,
                self.results["validator"]["required_fields"],
                self.results["validator"]["optional_fields"]
            )
            self.results["matcher"] = await matcher.match()
    
    async def _run_explore_mode(self, page):
        """Ejecuta solo modo Explorer"""
        explorer = Explorer(page, self.config)
        self.results["explorer"] = await explorer.explore()
    
    async def _run_extract_mode(self, page):
        """Ejecuta solo modo Extractor"""
        extractor = Extractor(page, self.config)
        self.results["extractor"] = await extractor.extract()
    
    async def _run_complete_mode(self, page):
        """Ejecuta Extractor + Completer"""
        # Primero extraer
        extractor = Extractor(page, self.config)
        self.results["extractor"] = await extractor.extract()
        
        # Luego completar
        if self.results["extractor"].get("success"):
            from modes.extractor import FormField
            field_objects = []
            for field_dict in self.results["extractor"]["fields"]:
                field_obj = FormField()
                for key, value in field_dict.items():
                    setattr(field_obj, key, value)
                field_objects.append(field_obj)
            
            completer = Completer(page, self.config, field_objects)
            self.results["completer"] = await completer.complete()
    
    async def _run_validate_mode(self, page):
        """Ejecuta Extractor + Validator"""
        # Primero extraer
        extractor = Extractor(page, self.config)
        self.results["extractor"] = await extractor.extract()
        
        # Luego validar
        if self.results["extractor"].get("success"):
            from modes.extractor import FormField
            field_objects = []
            for field_dict in self.results["extractor"]["fields"]:
                field_obj = FormField()
                for key, value in field_dict.items():
                    setattr(field_obj, key, value)
                field_objects.append(field_obj)
            
            validator = Validator(page, self.config, field_objects)
            self.results["validator"] = await validator.validate()
    
    async def _run_match_mode(self, page):
        """Ejecuta Extractor + Validator + Matcher"""
        # Extraer
        extractor = Extractor(page, self.config)
        self.results["extractor"] = await extractor.extract()
        
        # Validar
        if self.results["extractor"].get("success"):
            from modes.extractor import FormField
            field_objects = []
            for field_dict in self.results["extractor"]["fields"]:
                field_obj = FormField()
                for key, value in field_dict.items():
                    setattr(field_obj, key, value)
                field_objects.append(field_obj)
            
            validator = Validator(page, self.config, field_objects)
            self.results["validator"] = await validator.validate()
        
        # Matcher
        if self.results["extractor"].get("success") and self.results["validator"].get("success"):
            from modes.extractor import FormField
            field_objects = []
            for field_dict in self.results["extractor"]["fields"]:
                field_obj = FormField()
                for key, value in field_dict.items():
                    setattr(field_obj, key, value)
                field_objects.append(field_obj)
            
            matcher = Matcher(
                self.config,
                field_objects,
                self.results["validator"]["required_fields"],
                self.results["validator"]["optional_fields"]
            )
            self.results["matcher"] = await matcher.match()
    
    def _print_summary(self):
        """Imprime un resumen de la ejecución"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("RESUMEN DE EJECUCIÓN")
        logger.info("=" * 80)
        
        if self.execution_start and self.execution_end:
            duration = (self.execution_end - self.execution_start).total_seconds()
            logger.info(f"Duración total: {duration:.2f} segundos")
        
        # Estadísticas por modo
        if "extractor" in self.results:
            total_fields = self.results["extractor"].get("total_fields", 0)
            logger.info(f"Campos extraídos: {total_fields}")
        
        if "completer" in self.results:
            completed = self.results["completer"].get("completed_fields", 0)
            rate = self.results["completer"].get("completion_rate", 0)
            logger.info(f"Campos completados: {completed} ({rate:.1f}%)")
        
        if "validator" in self.results:
            required = len(self.results["validator"].get("required_fields", []))
            optional = len(self.results["validator"].get("optional_fields", []))
            logger.info(f"Campos obligatorios: {required}")
            logger.info(f"Campos opcionales: {optional}")
        
        if "matcher" in self.results:
            stats = self.results["matcher"].get("statistics", {})
            coverage = stats.get("coverage_percentage", 0)
            missing = stats.get("missing", 0)
            logger.info(f"Cobertura QA: {coverage:.1f}%")
            logger.info(f"Campos QA faltantes: {missing}")
        
        if "report" in self.results:
            report = self.results["report"]
            if report.get("success"):
                logger.info(f"\nInformes generados:")
                logger.info(f"  - JSON: {report.get('json_report')}")
                logger.info(f"  - Markdown: {report.get('markdown_report')}")
                logger.info(f"  - Anomalías: {report.get('anomalies_count', 0)}")
        
        logger.info("=" * 80)


def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Agente de Validación de Formularios Web"
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["explore", "extract", "complete", "validate", "match", "report", "full"],
        default="full",
        help="Modo de operación del agente"
    )
    
    parser.add_argument(
        "--form-url",
        type=str,
        help="URL del formulario objetivo"
    )
    
    
    parser.add_argument(
        "--qa-fields",
        type=str,
        help="Ruta al archivo de campos QA"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Ejecutar navegador en modo visible"
    )
    
    parser.add_argument(
        "--evidence",
        action="store_true",
        help="Capturar evidencia (screenshots)"
    )
    
    return parser.parse_args()


async def main():
    """Función principal"""
    args = parse_arguments()
    
    # Crear configuración
    if args.form_url:
        # Configuración desde argumentos + credenciales del .env
        import os
        from dotenv import load_dotenv
        load_dotenv()  # Cargar .env para obtener credenciales
        
        config = Config(
            form_url=args.form_url,
            mode=args.mode,
            headless=not args.no_headless,
            evidence_enabled=args.evidence,
            qa_fields_path=args.qa_fields or "test_data/campos_corfo.txt",
            # Cargar credenciales desde .env si existen
            test_username=os.getenv("TEST_USERNAME"),
            test_password=os.getenv("TEST_PASSWORD")
        )
    else:
        # Configuración desde .env
        config = Config.from_env()
        if not config.form_url:
            logger.error("ERROR: Se requiere --form-url o FORM_URL en .env")
            sys.exit(1)
    
    # Crear y ejecutar agente
    agent = FormValidationAgent(config)
    results = await agent.run()
    
    # Retornar código de salida según éxito
    if results.get("error"):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

