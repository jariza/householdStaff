from langchain_core.tools import tool

@tool
def encender_luz_jardin(zona: str) -> str:
    """Enciende los focos de una zona específica del jardín."""
    print(f"\n💡 [TOOL JARDÍN] Encendiendo focos en: {zona}...\n")
    return f"Los focos de la zona '{zona}' del jardin estan encendidos."