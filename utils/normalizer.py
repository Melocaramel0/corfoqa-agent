"""
Normalización y procesamiento de texto para matching y comparaciones.
Incluye funciones para normalizar nombres de campos, detectar similitudes y expandir sinónimos.
"""

import re
from typing import Set
from unidecode import unidecode
from config import STOPWORDS_ES


def normalize_text(text: str, remove_stopwords: bool = True) -> str:
    """
    Normaliza texto para comparaciones robustas.
    
    Args:
        text: Texto a normalizar
        remove_stopwords: Si True, elimina palabras comunes en español
        
    Returns:
        Texto normalizado (lowercase, sin tildes, sin stopwords, sin caracteres especiales)
    """
    if not text:
        return ""
    
    # Convertir a lowercase
    text = text.lower()
    
    # Eliminar tildes y caracteres especiales usando unidecode
    text = unidecode(text)
    
    # Eliminar caracteres especiales excepto espacios y guiones
    text = re.sub(r'[^a-z0-9\s\-]', ' ', text)
    
    # Normalizar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    # Eliminar stopwords si se solicita
    if remove_stopwords:
        words = text.split()
        words = [w for w in words if w not in STOPWORDS_ES]
        text = ' '.join(words)
    
    return text.strip()


def get_canonical_key(text: str) -> str:
    """
    Genera una clave canónica para matching de campos.
    
    Args:
        text: Texto original del campo
        
    Returns:
        Clave canónica (normalizada + expandida + sin stopwords)
    """
    # Normalizar
    normalized = normalize_text(text, remove_stopwords=True)
    
    # Expandir abreviaturas comunes
    expansions = {
        "rut": "rol unico tributario",
        "run": "rol unico nacional",
        "n°": "numero",
        "nro": "numero",
        "tel": "telefono",
        "cel": "celular",
        "dir": "direccion",
        "dpto": "departamento",
        "ap": "apellido",
        "nom": "nombre",
        "fec": "fecha",
        "nac": "nacimiento",
        "pat": "paterno",
        "mat": "materno",
    }
    
    for abbr, expanded in expansions.items():
        normalized = re.sub(r'\b' + abbr + r'\b', expanded, normalized)
    
    return normalized


def extract_keywords(text: str) -> Set[str]:
    """
    Extrae palabras clave relevantes de un texto.
    
    Args:
        text: Texto a procesar
        
    Returns:
        Conjunto de palabras clave
    """
    normalized = normalize_text(text, remove_stopwords=True)
    words = normalized.split()
    
    # Filtrar palabras muy cortas (menos de 3 caracteres)
    keywords = {w for w in words if len(w) >= 3}
    
    return keywords


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calcula similitud entre dos textos normalizados.
    Usa coeficiente de Jaccard sobre palabras clave.
    
    Args:
        text1: Primer texto
        text2: Segundo texto
        
    Returns:
        Score de similitud entre 0 y 1
    """
    # Obtener palabras clave de ambos textos
    keywords1 = extract_keywords(text1)
    keywords2 = extract_keywords(text2)
    
    # Si alguno está vacío, similitud es 0
    if not keywords1 or not keywords2:
        return 0.0
    
    # Calcular coeficiente de Jaccard (intersección / unión)
    intersection = keywords1 & keywords2
    union = keywords1 | keywords2
    
    if not union:
        return 0.0
    
    jaccard = len(intersection) / len(union)
    
    # Bonus por match exacto de clave canónica
    key1 = get_canonical_key(text1)
    key2 = get_canonical_key(text2)
    
    if key1 == key2:
        return 1.0
    
    return jaccard


def is_similar(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """
    Determina si dos textos son similares según un umbral.
    
    Args:
        text1: Primer texto
        text2: Segundo texto
        threshold: Umbral de similitud (0-1)
        
    Returns:
        True si la similitud supera el umbral
    """
    return calculate_similarity(text1, text2) >= threshold


# Diccionario de sinónimos para campos comunes
FIELD_SYNONYMS = {
    "nombre": ["nombres", "primer nombre", "nombre completo"],
    "apellido": ["apellidos", "apellido completo"],
    "apellido paterno": ["primer apellido", "ap paterno"],
    "apellido materno": ["segundo apellido", "ap materno"],
    "rut": ["run", "rol unico tributario", "rol unico nacional", "cedula"],
    "email": ["correo", "correo electronico", "e-mail", "mail"],
    "telefono": ["tel", "fono", "celular", "movil"],
    "direccion": ["domicilio", "dir", "calle"],
    "fecha nacimiento": ["fecha nac", "fec nacimiento", "fecha de nacimiento"],
    "razon social": ["nombre empresa", "nombre comercial", "empresa"],
    "giro": ["actividad", "rubro", "giro comercial"],
}


def find_synonyms(text: str) -> Set[str]:
    """
    Encuentra sinónimos conocidos para un texto dado.
    
    Args:
        text: Texto a buscar sinónimos
        
    Returns:
        Conjunto de sinónimos (incluye el texto original normalizado)
    """
    normalized = normalize_text(text, remove_stopwords=True)
    synonyms = {normalized}
    
    # Buscar en el diccionario de sinónimos
    for key, syn_list in FIELD_SYNONYMS.items():
        # Si el texto coincide con la clave o algún sinónimo
        if normalized == normalize_text(key, remove_stopwords=True):
            synonyms.update(normalize_text(s, remove_stopwords=True) for s in syn_list)
            break
        
        # Comprobar si es sinónimo de alguna clave
        for syn in syn_list:
            if normalized == normalize_text(syn, remove_stopwords=True):
                synonyms.add(normalize_text(key, remove_stopwords=True))
                synonyms.update(normalize_text(s, remove_stopwords=True) for s in syn_list)
                break
    
    return synonyms

