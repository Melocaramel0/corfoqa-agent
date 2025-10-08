"""
Reporter: Genera informes completos en JSON y Markdown con evidencias.
Compila todos los resultados de los diferentes modos en informes legibles.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Reporter:
    """Generador de informes completos del agente"""
    
    def __init__(self, config):
        """
        Inicializa el reporter.
        
        Args:
            config: Configuración del agente
        """
        self.config = config
        self.output_paths = config.get_output_paths()
    
    async def generate_report(
        self,
        explorer_result: Optional[Dict] = None,
        extractor_result: Optional[Dict] = None,
        completer_result: Optional[Dict] = None,
        validator_result: Optional[Dict] = None,
        matcher_result: Optional[Dict] = None,
        execution_start: Optional[datetime] = None,
        execution_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Genera informe completo en JSON y Markdown.
        
        Args:
            explorer_result: Resultado del modo Explorer
            extractor_result: Resultado del modo Extractor
            completer_result: Resultado del modo Completer
            validator_result: Resultado del modo Validator
            matcher_result: Resultado del modo Matcher
            execution_start: Timestamp de inicio
            execution_end: Timestamp de fin
            
        Returns:
            Diccionario con rutas a los informes generados
        """
        logger.info("=== Generando informes ===")
        
        try:
            # Calcular tiempo total de ejecución
            if execution_start and execution_end:
                total_time = (execution_end - execution_start).total_seconds()
            else:
                total_time = 0
            
            # Compilar datos del informe
            report_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "form_url": self.config.form_url,
                    "execution_time_seconds": total_time,
                    "agent_mode": self.config.mode
                },
                "explorer": explorer_result or {},
                "extractor": extractor_result or {},
                "completer": completer_result or {},
                "validator": validator_result or {},
                "matcher": matcher_result or {},
                "anomalies": self._detect_anomalies(
                    explorer_result,
                    extractor_result,
                    completer_result,
                    validator_result,
                    matcher_result
                )
            }
            
            # Generar informe JSON
            json_path = await self._generate_json_report(report_data)
            
            # Generar informe Markdown
            markdown_path = await self._generate_markdown_report(report_data)
            
            logger.info(f"Informes generados exitosamente")
            logger.info(f"  - JSON: {json_path}")
            logger.info(f"  - Markdown: {markdown_path}")
            
            return {
                "success": True,
                "json_report": str(json_path),
                "markdown_report": str(markdown_path),
                "anomalies_count": len(report_data["anomalies"])
            }
            
        except Exception as e:
            logger.error(f"Error generando informes: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_json_report(self, data: Dict[str, Any]) -> Path:
        """
        Genera informe JSON estructurado.
        
        Args:
            data: Datos del informe
            
        Returns:
            Ruta al archivo JSON
        """
        json_dir = self.output_paths["json"]
        json_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.json"
        filepath = json_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Informe JSON generado: {filepath}")
        return filepath
    
    async def _generate_markdown_report(self, data: Dict[str, Any]) -> Path:
        """
        Genera informe legible en Markdown.
        
        Args:
            data: Datos del informe
            
        Returns:
            Ruta al archivo Markdown
        """
        reports_dir = self.output_paths["reports"]
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.md"
        filepath = reports_dir / filename
        
        # Construir contenido Markdown
        content = self._build_markdown_content(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Informe Markdown generado: {filepath}")
        return filepath
    
    def _build_markdown_content(self, data: Dict[str, Any]) -> str:
        """
        Construye el contenido del informe Markdown.
        
        Args:
            data: Datos del informe
            
        Returns:
            Contenido Markdown
        """
        lines = []
        
        # Encabezado
        lines.append("# Informe de Validación de Formulario Web")
        lines.append("")
        lines.append(f"**Generado:** {data['metadata']['generated_at']}")
        lines.append(f"**URL:** {data['metadata']['form_url']}")
        lines.append(f"**Tiempo de Ejecución:** {data['metadata']['execution_time_seconds']:.2f} segundos")
        lines.append("")
        
        # Resumen Ejecutivo
        lines.append("## Resumen Ejecutivo")
        lines.append("")
        
        explorer = data.get("explorer", {})
        extractor = data.get("extractor", {})
        completer = data.get("completer", {})
        validator = data.get("validator", {})
        matcher = data.get("matcher", {})
        anomalies = data.get("anomalies", [])
        
        lines.append(f"- **Pasos del formulario:** {explorer.get('total_steps', 'N/A')}")
        lines.append(f"- **Campos totales:** {extractor.get('total_fields', 0)}")
        lines.append(f"- **Campos obligatorios:** {len(validator.get('required_fields', []))}")
        lines.append(f"- **Campos opcionales:** {len(validator.get('optional_fields', []))}")
        
        if completer:
            completion_rate = completer.get('completion_rate', 0)
            lines.append(f"- **Tasa de autocompletado:** {completion_rate:.1f}%")
        
        if matcher:
            stats = matcher.get('statistics', {})
            lines.append(f"- **Cobertura QA:** {stats.get('coverage_percentage', 0):.1f}%")
            lines.append(f"- **Campos QA faltantes:** {stats.get('missing', 0)}")
        
        lines.append(f"- **Anomalías detectadas:** {len(anomalies)}")
        lines.append("")
        
        # Sección Explorer
        if explorer.get("success"):
            lines.append("## Estructura del Formulario")
            lines.append("")
            lines.append(f"**Tipo:** {explorer.get('form_metadata', {}).get('structure_type', 'N/A')}")
            lines.append(f"**Total de pasos:** {explorer.get('total_steps', 0)}")
            lines.append("")
            
            steps = explorer.get("steps", [])
            if steps:
                lines.append("### Pasos Identificados")
                lines.append("")
                for step in steps:
                    lines.append(f"{step['index'] + 1}. **{step['title']}**")
                lines.append("")
        
        # Sección Validator
        if validator.get("success"):
            lines.append("## Detección de Obligatoriedad")
            lines.append("")
            
            required = validator.get("required_fields", [])
            optional = validator.get("optional_fields", [])
            uncertain = validator.get("uncertain_fields", [])
            
            lines.append(f"- **Campos obligatorios:** {len(required)}")
            lines.append(f"- **Campos opcionales:** {len(optional)}")
            lines.append(f"- **Campos inciertos:** {len(uncertain)}")
            lines.append("")
            
            if required:
                lines.append("### Campos Obligatorios Detectados")
                lines.append("")
                for field in required[:20]:  # Limitar a 20 para no saturar
                    lines.append(f"- {field}")
                if len(required) > 20:
                    lines.append(f"- ... y {len(required) - 20} más")
                lines.append("")
        
        # Sección Matcher QA
        if matcher.get("success"):
            lines.append("## Matching con Campos Fundamentales QA")
            lines.append("")
            
            stats = matcher.get("statistics", {})
            lines.append(f"**Cobertura:** {stats.get('coverage_percentage', 0):.1f}%")
            lines.append("")
            
            # Campos faltantes
            match_results = matcher.get("match_results", [])
            missing_fields = [r for r in match_results if r.get("status") == "FALTANTE"]
            
            if missing_fields:
                lines.append("### ⚠️ Campos QA Faltantes")
                lines.append("")
                for result in missing_fields:
                    lines.append(f"- **{result['qa_field']}**")
                lines.append("")
            
            # Campos potencialmente equivalentes (requieren revisión)
            potential_fields = [r for r in match_results if r.get("status") == "POTENCIAL_EQUIVALENTE"]
            
            if potential_fields:
                lines.append("### 🔍 Campos Potencialmente Equivalentes (Requieren Revisión)")
                lines.append("")
                for result in potential_fields:
                    sim = result.get('similarity', 0)
                    lines.append(
                        f"- **{result['qa_field']}** ≈ {result['found_field']} "
                        f"(similitud: {sim:.2f})"
                    )
                lines.append("")
            
            # Campos que deberían ser obligatorios
            should_be_req = stats.get("should_be_required", [])
            if should_be_req:
                lines.append("### 💡 Propuesta: Campos que Deberían Ser Obligatorios")
                lines.append("")
                lines.append("Los siguientes campos están en la lista QA pero fueron detectados como opcionales:")
                lines.append("")
                for field in should_be_req:
                    lines.append(f"- {field}")
                lines.append("")
        
        # Sección de Anomalías
        if anomalies:
            lines.append("## Anomalías Detectadas")
            lines.append("")
            
            for i, anomaly in enumerate(anomalies, 1):
                lines.append(f"### {i}. {anomaly['title']}")
                lines.append("")
                lines.append(f"**Severidad:** {anomaly['severity']}")
                lines.append(f"**Categoría:** {anomaly['category']}")
                lines.append("")
                lines.append(f"**Descripción:** {anomaly['description']}")
                lines.append("")
                
                if anomaly.get('evidence'):
                    lines.append(f"**Evidencia:** `{anomaly['evidence']}`")
                    lines.append("")
        
        # Sección de Métricas
        lines.append("## Métricas de Ejecución")
        lines.append("")
        lines.append(f"- **Tiempo total:** {data['metadata']['execution_time_seconds']:.2f}s")
        
        if explorer.get('execution_time'):
            lines.append(f"- **Tiempo Explorer:** {explorer['execution_time']:.2f}s")
        
        if extractor.get('success'):
            lines.append(f"- **Campos extraídos:** {extractor.get('total_fields', 0)}")
        
        if completer:
            lines.append(
                f"- **Campos completados:** {completer.get('completed_fields', 0)}/"
                f"{completer.get('total_fields', 0)}"
            )
        
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Generado automáticamente por el Agente de Validación de Formularios Web*")
        lines.append("")
        
        return "\n".join(lines)
    
    def _detect_anomalies(
        self,
        explorer_result: Optional[Dict],
        extractor_result: Optional[Dict],
        completer_result: Optional[Dict],
        validator_result: Optional[Dict],
        matcher_result: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Detecta anomalías en los resultados de todos los modos.
        
        Returns:
            Lista de anomalías detectadas
        """
        anomalies = []
        
        # Anomalía 1: Campos QA faltantes
        if matcher_result and matcher_result.get("success"):
            match_results = matcher_result.get("match_results", [])
            missing_fields = [r for r in match_results if r.get("status") == "FALTANTE"]
            
            if missing_fields:
                anomalies.append({
                    "title": "Campos Fundamentales QA Faltantes",
                    "severity": "HIGH",
                    "category": "MISSING_FIELDS",
                    "description": (
                        f"Se detectaron {len(missing_fields)} campos fundamentales de QA "
                        "que no están presentes en el formulario."
                    ),
                    "fields": [f['qa_field'] for f in missing_fields],
                    "evidence": None
                })
        
        # Anomalía 2: Campos QA presentes pero no obligatorios
        if matcher_result and validator_result:
            stats = matcher_result.get("statistics", {})
            should_be_req = stats.get("should_be_required", [])
            
            if should_be_req:
                anomalies.append({
                    "title": "Campos QA No Marcados como Obligatorios",
                    "severity": "MEDIUM",
                    "category": "INCORRECT_VALIDATION",
                    "description": (
                        f"{len(should_be_req)} campos de la lista QA están presentes "
                        "pero fueron detectados como opcionales cuando deberían ser obligatorios."
                    ),
                    "fields": should_be_req,
                    "evidence": None
                })
        
        # Anomalía 3: Baja tasa de autocompletado
        if completer_result:
            completion_rate = completer_result.get("completion_rate", 0)
            
            if completion_rate < 80:
                anomalies.append({
                    "title": "Baja Tasa de Autocompletado",
                    "severity": "MEDIUM",
                    "category": "AUTOMATION_ISSUE",
                    "description": (
                        f"Solo se pudo completar el {completion_rate:.1f}% de los campos. "
                        "Esto puede indicar campos con validaciones complejas o tipos no soportados."
                    ),
                    "fields": completer_result.get("failed", []),
                    "evidence": None
                })
        
        # Anomalía 4: Campos sin tipo identificado
        if extractor_result:
            fields = extractor_result.get("fields", [])
            unknown_fields = [f for f in fields if f.get("type") == "unknown"]
            
            if unknown_fields:
                anomalies.append({
                    "title": "Campos con Tipo Desconocido",
                    "severity": "LOW",
                    "category": "EXTRACTION_ISSUE",
                    "description": (
                        f"{len(unknown_fields)} campos no pudieron ser tipados correctamente. "
                        "Esto puede afectar el autocompletado."
                    ),
                    "fields": [f.get("canonical_key") for f in unknown_fields],
                    "evidence": None
                })
        
        # Anomalía 5: Errores de validación inesperados
        if validator_result:
            validation_events = validator_result.get("validation_events", [])
            error_events = [e for e in validation_events if not e.get("success")]
            
            if error_events:
                anomalies.append({
                    "title": "Errores de Validación Detectados",
                    "severity": "MEDIUM",
                    "category": "VALIDATION_ERROR",
                    "description": (
                        f"Se detectaron {len(error_events)} eventos de error de validación. "
                        "Revisar mensajes para identificar problemas."
                    ),
                    "fields": list(set(e.get("field_key") for e in error_events)),
                    "evidence": error_events[0].get("screenshot") if error_events else None
                })
        
        return anomalies

