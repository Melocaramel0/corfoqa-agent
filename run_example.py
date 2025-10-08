"""
Script de ejemplo para ejecutar el agente con diferentes configuraciones.
Muestra cómo usar el agente programáticamente.
"""

import asyncio
from config import Config
from main import FormValidationAgent


async def example_full_validation():
    """
    Ejemplo: Validación completa de un formulario.
    Ejecuta todos los modos en secuencia.
    """
    print("\n" + "="*80)
    print("EJEMPLO: Validación Completa")
    print("="*80 + "\n")
    
    # Configurar el agente
    config = Config(
        form_url="https://ejemplo.com/formulario",  # Cambiar por URL real
        mode="full",
        headless=False,  # Mostrar navegador
        evidence_enabled=True,
        qa_fields_path="test_data/campos_corfo.txt",
        test_pdf_path="test_data/sample.pdf"
    )
    
    # Crear y ejecutar agente
    agent = FormValidationAgent(config)
    results = await agent.run()
    
    return results


async def example_exploration_only():
    """
    Ejemplo: Solo explorar la estructura del formulario.
    Útil para conocer un formulario nuevo.
    """
    print("\n" + "="*80)
    print("EJEMPLO: Solo Exploración")
    print("="*80 + "\n")
    
    config = Config(
        form_url="https://ejemplo.com/formulario",
        mode="explore",
        headless=False
    )
    
    agent = FormValidationAgent(config)
    results = await agent.run()
    
    # Mostrar resultados de exploración
    if "explorer" in results:
        explorer = results["explorer"]
        print(f"\n✓ Pasos encontrados: {explorer.get('total_steps', 0)}")
        for step in explorer.get("steps", []):
            print(f"  {step['index'] + 1}. {step['title']}")
    
    return results


async def example_validation_only():
    """
    Ejemplo: Validar campos sin completar el formulario.
    Útil para auditar qué campos son obligatorios.
    """
    print("\n" + "="*80)
    print("EJEMPLO: Solo Validación")
    print("="*80 + "\n")
    
    config = Config(
        form_url="https://ejemplo.com/formulario",
        mode="validate",
        headless=False,
        evidence_enabled=True
    )
    
    agent = FormValidationAgent(config)
    results = await agent.run()
    
    # Mostrar campos obligatorios
    if "validator" in results:
        validator = results["validator"]
        required = validator.get("required_fields", [])
        print(f"\n✓ Campos obligatorios detectados: {len(required)}")
        for field in required[:10]:
            print(f"  - {field}")
        if len(required) > 10:
            print(f"  ... y {len(required) - 10} más")
    
    return results


async def example_qa_matching():
    """
    Ejemplo: Comparar formulario contra lista QA.
    Identifica campos faltantes de la especificación.
    """
    print("\n" + "="*80)
    print("EJEMPLO: Matching QA")
    print("="*80 + "\n")
    
    config = Config(
        form_url="https://ejemplo.com/formulario",
        mode="match",
        headless=True,  # Ejecución rápida sin UI
        qa_fields_path="test_data/campos_corfo.txt"
    )
    
    agent = FormValidationAgent(config)
    results = await agent.run()
    
    # Mostrar resultados de matching
    if "matcher" in results:
        matcher = results["matcher"]
        stats = matcher.get("statistics", {})
        
        print(f"\n✓ Cobertura QA: {stats.get('coverage_percentage', 0):.1f}%")
        print(f"  - Presentes: {stats.get('present', 0)}")
        print(f"  - Faltantes: {stats.get('missing', 0)}")
        print(f"  - Potenciales equivalentes: {stats.get('potential_equivalent', 0)}")
        
        # Listar campos faltantes
        missing = [
            r for r in matcher.get("match_results", [])
            if r.get("status") == "FALTANTE"
        ]
        
        if missing:
            print(f"\n⚠ Campos QA faltantes:")
            for result in missing[:10]:
                print(f"  - {result['qa_field']}")
            if len(missing) > 10:
                print(f"  ... y {len(missing) - 10} más")
    
    return results


def main():
    """
    Función principal que muestra los diferentes ejemplos.
    Comenta/descomenta para ejecutar el ejemplo deseado.
    """
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                AGENTE DE VALIDACIÓN DE FORMULARIOS WEB                       ║
║                          Ejemplos de Uso                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

IMPORTANTE: Antes de ejecutar estos ejemplos:
1. Actualiza las URLs con formularios reales
2. Asegúrate de que el PDF de prueba existe (ejecuta create_sample_pdf.py)
3. Revisa/ajusta campos_corfo.txt según tu formulario

Descomenta el ejemplo que quieras ejecutar:
    """)
    
    # Descomentar el ejemplo deseado:
    
    # asyncio.run(example_full_validation())
    # asyncio.run(example_exploration_only())
    # asyncio.run(example_validation_only())
    # asyncio.run(example_qa_matching())
    
    print("\nℹ Para ejecutar, descomenta uno de los ejemplos en run_example.py")
    print("\nO ejecuta directamente desde CLI:")
    print("  python main.py --mode full --form-url URL --no-headless\n")


if __name__ == "__main__":
    main()

