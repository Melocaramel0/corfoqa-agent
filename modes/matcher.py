"""
Modo Matcher QA: Compara campos encontrados contra lista de Campos Fundamentales.
Detecta faltantes, renombrados y extras mediante matching inteligente.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from fuzzywuzzy import fuzz

from modes.extractor import FormField
from utils.normalizer import (
    normalize_text,
    get_canonical_key,
    calculate_similarity,
    find_synonyms
)

logger = logging.getLogger(__name__)


class QAField:
    """Representa un campo fundamental de QA"""
    
    def __init__(self, original_text: str):
        """
        Inicializa un campo QA.
        
        Args:
            original_text: Texto original del campo QA
        """
        self.original_text = original_text
        self.normalized = normalize_text(original_text, remove_stopwords=True)
        self.canonical_key = get_canonical_key(original_text)
        self.synonyms = find_synonyms(original_text)
    
    def __repr__(self):
        return f"QAField({self.original_text})"


class MatchResult:
    """Resultado del matching entre campo QA y campo encontrado"""
    
    def __init__(
        self,
        qa_field: str,
        status: str,
        found_field: Optional[str] = None,
        similarity: float = 0.0,
        match_type: Optional[str] = None
    ):
        """
        Inicializa un resultado de matching.
        
        Args:
            qa_field: Campo fundamental QA
            status: Estado ('PRESENTE', 'FALTANTE', 'POTENCIAL_EQUIVALENTE', 'EXTRA_NO_QA')
            found_field: Campo encontrado en el formulario
            similarity: Score de similitud (0-1)
            match_type: Tipo de match ('exact', 'synonym', 'similarity', 'none')
        """
        self.qa_field = qa_field
        self.status = status
        self.found_field = found_field
        self.similarity = similarity
        self.match_type = match_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario"""
        return {
            "qa_field": self.qa_field,
            "status": self.status,
            "found_field": self.found_field,
            "similarity": self.similarity,
            "match_type": self.match_type
        }


class Matcher:
    """Modo Matcher QA: Compara campos contra lista QA"""
    
    def __init__(
        self,
        config,
        fields: List[FormField],
        required_fields: List[str],
        optional_fields: List[str]
    ):
        """
        Inicializa el matcher.
        
        Args:
            config: Configuración del agente
            fields: Lista de campos extraídos del formulario
            required_fields: Lista de campos obligatorios detectados
            optional_fields: Lista de campos opcionales detectados
        """
        self.config = config
        self.fields = fields
        self.required_fields = set(required_fields)
        self.optional_fields = set(optional_fields)
        
        # Campos QA
        self.qa_fields: List[QAField] = []
        
        # Resultados
        self.match_results: List[MatchResult] = []
        self.extra_fields: List[str] = []
    
    async def match(self) -> Dict[str, Any]:
        """
        Ejecuta el matching QA completo.
        
        Returns:
            Diccionario con resultados del matching
        """
        logger.info("=== Iniciando modo Matcher QA ===")
        
        try:
            # Cargar campos QA
            await self._load_qa_fields()
            
            # Realizar matching
            await self._perform_matching()
            
            # Identificar campos extra (no en QA)
            await self._identify_extra_fields()
            
            # Generar estadísticas
            stats = self._calculate_statistics()
            
            logger.info(f"Matching completado: {stats['present']} presentes, {stats['missing']} faltantes")
            
            return {
                "success": True,
                "total_qa_fields": len(self.qa_fields),
                "total_found_fields": len(self.fields),
                "match_results": [result.to_dict() for result in self.match_results],
                "extra_fields": self.extra_fields,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error en modo Matcher: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "match_results": []
            }
    
    async def _load_qa_fields(self) -> None:
        """Carga los campos fundamentales desde el archivo QA"""
        qa_path = Path(self.config.qa_fields_path)
        
        if not qa_path.exists():
            logger.warning(f"Archivo de campos QA no encontrado: {qa_path}")
            # Crear archivo de ejemplo
            self._create_sample_qa_file(qa_path)
            logger.info(f"Archivo de ejemplo creado en: {qa_path}")
        
        try:
            with open(qa_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                # Ignorar líneas vacías y comentarios
                if line and not line.startswith('#'):
                    qa_field = QAField(line)
                    self.qa_fields.append(qa_field)
            
            logger.info(f"Cargados {len(self.qa_fields)} campos fundamentales QA")
            
        except Exception as e:
            logger.error(f"Error cargando campos QA: {e}")
            raise
    
    def _create_sample_qa_file(self, path: Path) -> None:
        """
        Crea un archivo de ejemplo de campos QA.
        
        Args:
            path: Ruta donde crear el archivo
        """
        sample_fields = [
            "# Campos Fundamentales QA - CORFO",
            "# Un campo por línea. Líneas que empiezan con # son comentarios.",
            "",
            "# Identificación",
            "RUT",
            "Nombre",
            "Apellido Paterno",
            "Apellido Materno",
            "Email",
            "Teléfono",
            "",
            "# Datos de Empresa",
            "Razón Social",
            "RUT Empresa",
            "Giro Comercial",
            "Fecha Inicio Actividades",
            "",
            "# Ubicación",
            "Dirección",
            "Comuna",
            "Región",
            "",
            "# Proyecto",
            "Nombre del Proyecto",
            "Descripción del Proyecto",
            "Monto Solicitado",
            "Duración del Proyecto",
        ]
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sample_fields))
    
    async def _perform_matching(self) -> None:
        """Realiza el matching entre campos QA y campos encontrados"""
        logger.info("Realizando matching de campos...")
        
        # Crear índice de campos encontrados por clave canónica
        found_fields_index: Dict[str, FormField] = {
            field.canonical_key: field for field in self.fields
        }
        
        # Conjunto para rastrear campos ya matcheados
        matched_found_fields: Set[str] = set()
        
        for qa_field in self.qa_fields:
            # Intentar match exacto
            exact_match = self._try_exact_match(
                qa_field,
                found_fields_index,
                matched_found_fields
            )
            
            if exact_match:
                matched_found_fields.add(exact_match.found_field)
                self.match_results.append(exact_match)
                continue
            
            # Intentar match por sinónimos
            synonym_match = self._try_synonym_match(
                qa_field,
                found_fields_index,
                matched_found_fields
            )
            
            if synonym_match:
                matched_found_fields.add(synonym_match.found_field)
                self.match_results.append(synonym_match)
                continue
            
            # Intentar match por similitud
            similarity_match = self._try_similarity_match(
                qa_field,
                found_fields_index,
                matched_found_fields
            )
            
            if similarity_match:
                matched_found_fields.add(similarity_match.found_field)
                self.match_results.append(similarity_match)
                continue
            
            # No se encontró match: campo faltante
            missing_result = MatchResult(
                qa_field=qa_field.original_text,
                status="FALTANTE",
                match_type="none"
            )
            self.match_results.append(missing_result)
            logger.warning(f"Campo QA faltante: {qa_field.original_text}")
    
    def _try_exact_match(
        self,
        qa_field: QAField,
        found_fields_index: Dict[str, FormField],
        matched: Set[str]
    ) -> Optional[MatchResult]:
        """
        Intenta match exacto por clave canónica.
        
        Args:
            qa_field: Campo QA a matchear
            found_fields_index: Índice de campos encontrados
            matched: Conjunto de campos ya matcheados
            
        Returns:
            MatchResult si hay match, None si no
        """
        if qa_field.canonical_key in found_fields_index:
            found_field = found_fields_index[qa_field.canonical_key]
            
            if found_field.canonical_key not in matched:
                logger.debug(f"Match exacto: {qa_field.original_text} = {found_field.canonical_key}")
                
                return MatchResult(
                    qa_field=qa_field.original_text,
                    status="PRESENTE",
                    found_field=found_field.canonical_key,
                    similarity=1.0,
                    match_type="exact"
                )
        
        return None
    
    def _try_synonym_match(
        self,
        qa_field: QAField,
        found_fields_index: Dict[str, FormField],
        matched: Set[str]
    ) -> Optional[MatchResult]:
        """
        Intenta match por sinónimos conocidos.
        
        Args:
            qa_field: Campo QA a matchear
            found_fields_index: Índice de campos encontrados
            matched: Conjunto de campos ya matcheados
            
        Returns:
            MatchResult si hay match, None si no
        """
        for synonym in qa_field.synonyms:
            if synonym in found_fields_index:
                found_field = found_fields_index[synonym]
                
                if found_field.canonical_key not in matched:
                    logger.debug(f"Match por sinónimo: {qa_field.original_text} ≈ {found_field.canonical_key}")
                    
                    return MatchResult(
                        qa_field=qa_field.original_text,
                        status="PRESENTE",
                        found_field=found_field.canonical_key,
                        similarity=0.95,
                        match_type="synonym"
                    )
        
        return None
    
    def _try_similarity_match(
        self,
        qa_field: QAField,
        found_fields_index: Dict[str, FormField],
        matched: Set[str]
    ) -> Optional[MatchResult]:
        """
        Intenta match por similitud de texto.
        
        Args:
            qa_field: Campo QA a matchear
            found_fields_index: Índice de campos encontrados
            matched: Conjunto de campos ya matcheados
            
        Returns:
            MatchResult si hay match suficiente, None si no
        """
        best_match: Optional[tuple] = None
        best_similarity = self.config.qa_match_threshold
        
        for canonical_key, found_field in found_fields_index.items():
            if canonical_key in matched:
                continue
            
            # Calcular similitud usando diferentes métodos
            jaccard_sim = calculate_similarity(
                qa_field.original_text,
                found_field.label_visible or canonical_key
            )
            
            # Usar también fuzzywuzzy para similitud de strings
            fuzzy_sim = fuzz.ratio(
                qa_field.normalized,
                normalize_text(found_field.label_visible or canonical_key, remove_stopwords=True)
            ) / 100.0
            
            # Combinar scores (promedio ponderado)
            combined_sim = (jaccard_sim * 0.6) + (fuzzy_sim * 0.4)
            
            if combined_sim > best_similarity:
                best_similarity = combined_sim
                best_match = (found_field, combined_sim)
        
        if best_match:
            found_field, similarity = best_match
            
            # Si la similitud es muy alta (>0.9), considerarlo presente
            # Si es moderada (0.7-0.9), marcarlo como potencial equivalente
            if similarity >= 0.9:
                status = "PRESENTE"
            else:
                status = "POTENCIAL_EQUIVALENTE"
            
            logger.debug(
                f"Match por similitud ({similarity:.2f}): "
                f"{qa_field.original_text} ≈ {found_field.canonical_key}"
            )
            
            return MatchResult(
                qa_field=qa_field.original_text,
                status=status,
                found_field=found_field.canonical_key,
                similarity=similarity,
                match_type="similarity"
            )
        
        return None
    
    async def _identify_extra_fields(self) -> None:
        """Identifica campos extras (no en la lista QA)"""
        # Obtener todos los campos matcheados
        matched_field_keys = {
            result.found_field for result in self.match_results
            if result.found_field
        }
        
        # Campos extra son los que no se matchearon
        for field in self.fields:
            if field.canonical_key not in matched_field_keys:
                self.extra_fields.append(field.canonical_key)
                logger.debug(f"Campo extra (no en QA): {field.canonical_key}")
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """
        Calcula estadísticas del matching.
        
        Returns:
            Diccionario con estadísticas
        """
        present = sum(1 for r in self.match_results if r.status == "PRESENTE")
        missing = sum(1 for r in self.match_results if r.status == "FALTANTE")
        potential = sum(1 for r in self.match_results if r.status == "POTENCIAL_EQUIVALENTE")
        
        coverage = (present / len(self.qa_fields) * 100) if self.qa_fields else 0
        
        # Campos opcionales que deberían ser obligatorios según QA
        should_be_required = []
        for result in self.match_results:
            if result.status == "PRESENTE" and result.found_field:
                if result.found_field in self.optional_fields:
                    should_be_required.append(result.found_field)
        
        return {
            "present": present,
            "missing": missing,
            "potential_equivalent": potential,
            "extra_fields": len(self.extra_fields),
            "coverage_percentage": coverage,
            "should_be_required": should_be_required
        }

