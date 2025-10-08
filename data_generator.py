"""
Generador de datos de prueba coherentes por tipo de campo.
Incluye RUT/RUN chilenos, emails, teléfonos, fechas, direcciones, montos, etc.
"""

import random
from datetime import datetime, timedelta
from typing import Optional, Literal


class DataGenerator:
    """Genera datos de prueba realistas para formularios"""
    
    def __init__(self, seed: Optional[int] = None):
        """
        Inicializa el generador con una semilla opcional para reproducibilidad.
        
        Args:
            seed: Semilla para el generador random (None para aleatorio)
        """
        if seed is not None:
            random.seed(seed)
        
        # Datos base para generación
        self.nombres = ["Juan", "María", "Pedro", "Ana", "Carlos", "Lucía", "Diego", "Sofía"]
        self.apellidos_paternos = ["González", "Rodríguez", "Pérez", "López", "Martínez", "García", "Fernández"]
        self.apellidos_maternos = ["Silva", "Muñoz", "Rojas", "Díaz", "Torres", "Álvarez", "Vargas"]
        self.razones_sociales = [
            "Comercial", "Distribuidora", "Servicios", "Ingeniería", "Consultora", 
            "Inversiones", "Tecnología", "Soluciones"
        ]
        self.giros = [
            "Comercio al por menor",
            "Servicios de consultoría",
            "Desarrollo de software",
            "Construcción y obras civiles",
            "Transporte de carga",
            "Servicios profesionales",
        ]
        self.regiones = [
            "Región Metropolitana",
            "Región de Valparaíso",
            "Región del Biobío",
            "Región de la Araucanía",
            "Región de Los Lagos",
        ]
        self.comunas = {
            "Región Metropolitana": ["Santiago", "Providencia", "Las Condes", "Maipú", "La Florida"],
            "Región de Valparaíso": ["Valparaíso", "Viña del Mar", "Quilpué", "Concón"],
            "Región del Biobío": ["Concepción", "Talcahuano", "Los Ángeles", "Chillán"],
            "Región de la Araucanía": ["Temuco", "Villarrica", "Pucón", "Angol"],
            "Región de Los Lagos": ["Puerto Montt", "Osorno", "Castro", "Ancud"],
        }
        self.calles = [
            "Avenida Providencia", "Calle Alameda", "Pasaje Los Robles",
            "Avenida Libertador", "Calle Principal", "Camino Real"
        ]
    
    def generate_rut(self) -> str:
        """
        Genera un RUT chileno válido con dígito verificador correcto.
        
        Returns:
            RUT en formato XX.XXX.XXX-X
        """
        # Generar número base (entre 5 y 25 millones)
        numero = random.randint(5000000, 25000000)
        
        # Calcular dígito verificador
        dv = self._calcular_dv(numero)
        
        # Formatear RUT
        rut_str = f"{numero:,}".replace(",", ".")
        return f"{rut_str}-{dv}"
    
    def _calcular_dv(self, rut: int) -> str:
        """
        Calcula el dígito verificador de un RUT chileno.
        
        Args:
            rut: Número del RUT sin dígito verificador
            
        Returns:
            Dígito verificador ('0'-'9' o 'K')
        """
        suma = 0
        multiplicador = 2
        
        # Procesar dígitos de derecha a izquierda
        while rut > 0:
            suma += (rut % 10) * multiplicador
            rut //= 10
            multiplicador = multiplicador + 1 if multiplicador < 7 else 2
        
        # Calcular dígito verificador
        resto = suma % 11
        dv = 11 - resto
        
        if dv == 11:
            return "0"
        elif dv == 10:
            return "K"
        else:
            return str(dv)
    
    def generate_nombre(self) -> str:
        """Genera un nombre aleatorio"""
        return random.choice(self.nombres)
    
    def generate_apellido_paterno(self) -> str:
        """Genera un apellido paterno aleatorio"""
        return random.choice(self.apellidos_paternos)
    
    def generate_apellido_materno(self) -> str:
        """Genera un apellido materno aleatorio"""
        return random.choice(self.apellidos_maternos)
    
    def generate_nombre_completo(self) -> str:
        """Genera un nombre completo (nombre + apellido paterno + apellido materno)"""
        return f"{self.generate_nombre()} {self.generate_apellido_paterno()} {self.generate_apellido_materno()}"
    
    def generate_email(self, nombre: Optional[str] = None) -> str:
        """
        Genera un email de prueba.
        
        Args:
            nombre: Nombre base para el email (opcional)
            
        Returns:
            Email en formato nombre.apellido@ejemplo.cl
        """
        if nombre is None:
            nombre = self.generate_nombre().lower()
        apellido = self.generate_apellido_paterno().lower()
        
        dominios = ["ejemplo.cl", "test.cl", "prueba.cl", "demo.cl"]
        dominio = random.choice(dominios)
        
        return f"{nombre}.{apellido}@{dominio}"
    
    def generate_telefono(self, tipo: Literal["fijo", "movil"] = "movil") -> str:
        """
        Genera un número de teléfono chileno.
        
        Args:
            tipo: Tipo de teléfono ('fijo' o 'movil')
            
        Returns:
            Número de teléfono en formato +56 X XXXX XXXX
        """
        if tipo == "movil":
            # Móvil: +56 9 XXXX XXXX
            numero = f"+56 9 {random.randint(5000, 9999)} {random.randint(1000, 9999)}"
        else:
            # Fijo: +56 2 XXXX XXXX (Santiago) u otros códigos
            codigo_area = random.choice([2, 32, 33, 41, 42, 43, 45, 51, 52, 53, 55, 57, 58, 61, 63, 64, 65, 67, 71, 72, 73, 75])
            numero = f"+56 {codigo_area} {random.randint(200, 999)} {random.randint(1000, 9999)}"
        
        return numero
    
    def generate_fecha(
        self,
        tipo: Literal["nacimiento", "inicio_actividades", "pasado", "futuro", "cualquiera"] = "cualquiera",
        formato: str = "%Y-%m-%d"
    ) -> str:
        """
        Genera una fecha según el tipo especificado.
        
        Args:
            tipo: Tipo de fecha a generar
            formato: Formato de la fecha (strftime)
            
        Returns:
            Fecha formateada
        """
        hoy = datetime.now()
        
        if tipo == "nacimiento":
            # Fecha de nacimiento: entre 18 y 80 años atrás
            años_atras = random.randint(18, 80)
            fecha = hoy - timedelta(days=años_atras * 365)
        elif tipo == "inicio_actividades":
            # Inicio de actividades: entre 1 y 30 años atrás
            años_atras = random.randint(1, 30)
            fecha = hoy - timedelta(days=años_atras * 365)
        elif tipo == "pasado":
            # Fecha en el pasado: últimos 5 años
            dias_atras = random.randint(1, 1825)  # 5 años
            fecha = hoy - timedelta(days=dias_atras)
        elif tipo == "futuro":
            # Fecha futura: próximos 2 años
            dias_adelante = random.randint(1, 730)  # 2 años
            fecha = hoy + timedelta(days=dias_adelante)
        else:
            # Cualquiera: entre 10 años atrás y 2 años adelante
            dias = random.randint(-3650, 730)
            fecha = hoy + timedelta(days=dias)
        
        return fecha.strftime(formato)
    
    def generate_monto(
        self,
        min_value: int = 100000,
        max_value: int = 50000000,
        moneda: Literal["CLP", "UF", "USD"] = "CLP"
    ) -> str:
        """
        Genera un monto monetario.
        
        Args:
            min_value: Valor mínimo
            max_value: Valor máximo
            moneda: Tipo de moneda
            
        Returns:
            Monto formateado con separador de miles
        """
        monto = random.randint(min_value, max_value)
        
        # Formatear con separador de miles
        if moneda == "UF":
            # UF usa decimales
            monto_uf = monto / 36000  # Aproximación
            return f"{monto_uf:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            # CLP y USD sin decimales en este caso
            return f"{monto:,}".replace(",", ".")
    
    def generate_razon_social(self) -> str:
        """Genera una razón social de empresa"""
        tipo = random.choice(self.razones_sociales)
        apellido = random.choice(self.apellidos_paternos)
        forma = random.choice(["Ltda.", "S.A.", "SpA", "E.I.R.L."])
        
        return f"{tipo} {apellido} {forma}"
    
    def generate_giro(self) -> str:
        """Genera un giro comercial"""
        return random.choice(self.giros)
    
    def generate_direccion(self) -> dict[str, str]:
        """
        Genera una dirección completa.
        
        Returns:
            Diccionario con calle, número, región y comuna
        """
        region = random.choice(self.regiones)
        comuna = random.choice(self.comunas[region])
        calle = random.choice(self.calles)
        numero = random.randint(100, 9999)
        
        return {
            "calle": calle,
            "numero": str(numero),
            "region": region,
            "comuna": comuna,
            "direccion_completa": f"{calle} {numero}, {comuna}, {region}"
        }
    
    def generate_texto(self, min_words: int = 5, max_words: int = 20) -> str:
        """
        Genera texto aleatorio para campos de texto libre.
        
        Args:
            min_words: Mínimo de palabras
            max_words: Máximo de palabras
            
        Returns:
            Texto generado
        """
        palabras = [
            "descripción", "proyecto", "innovación", "desarrollo", "tecnología",
            "servicio", "calidad", "cliente", "producto", "solución",
            "gestión", "proceso", "resultado", "objetivo", "estrategia"
        ]
        
        num_palabras = random.randint(min_words, max_words)
        texto = " ".join(random.choices(palabras, k=num_palabras))
        
        # Capitalizar primera letra
        return texto.capitalize() + "."
    
    def generate_porcentaje(self, min_val: int = 0, max_val: int = 100) -> str:
        """
        Genera un valor porcentual.
        
        Args:
            min_val: Valor mínimo
            max_val: Valor máximo
            
        Returns:
            Porcentaje como string
        """
        return str(random.randint(min_val, max_val))
    
    def generate_numero(self, min_val: int = 1, max_val: int = 1000) -> str:
        """
        Genera un número entero.
        
        Args:
            min_val: Valor mínimo
            max_val: Valor máximo
            
        Returns:
            Número como string
        """
        return str(random.randint(min_val, max_val))


# Instancia global para uso compartido
default_generator = DataGenerator()

