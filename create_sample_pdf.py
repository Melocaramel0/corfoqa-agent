"""
Script para crear un PDF de prueba simple.
Se ejecuta una vez para generar el PDF necesario para los tests.
"""

from pathlib import Path

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    def create_sample_pdf():
        """Crea un PDF de prueba simple"""
        output_path = Path("test_data/sample.pdf")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear PDF
        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter
        
        # Agregar contenido
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "Documento de Prueba")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 140, "Este es un documento PDF de prueba para el")
        c.drawString(100, height - 160, "Agente de Validación de Formularios Web.")
        c.drawString(100, height - 200, "Información del documento:")
        c.drawString(100, height - 220, "- Tipo: PDF de prueba")
        c.drawString(100, height - 240, "- Propósito: Upload en formularios")
        c.drawString(100, height - 260, "- Tamaño: Pequeño (~1KB)")
        
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(100, 50, "Generado automáticamente por create_sample_pdf.py")
        
        c.save()
        
        print(f"OK - PDF de prueba creado: {output_path}")
        return output_path
    
    if __name__ == "__main__":
        create_sample_pdf()

except ImportError:
    print("WARNING: reportlab no esta instalado. Creando archivo placeholder...")
    
    # Crear un archivo placeholder
    output_path = Path("test_data/sample.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Crear un PDF mínimo válido manualmente
    pdf_content = """%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 55
>>
stream
BT
/F1 12 Tf
100 700 Td
(Documento de Prueba) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
422
%%EOF
"""
    
    with open(output_path, 'w') as f:
        f.write(pdf_content)
    
    print(f"OK - PDF placeholder creado: {output_path}")
    print("  Para un PDF completo, instala reportlab: pip install reportlab")

