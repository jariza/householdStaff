EMPTY_PRELOAD_MEM = "La precarga no encontró ninguna información relevante en la memoria a largo plazo."

PRELOADED_MEM_USAGE = """
Dispones de un sistema de memoria a largo plazo.
<memory_context>
{mem}
</memory_context>
<memory_guidelines>
1. Evaluación de contexto: Analiza el contenido dentro de `<memory_context>`. Si responde con certeza a la consulta del usuario, utilízalo para elaborar tu respuesta de forma fluida y natural (sin explicitar que procede de un registro o base de datos).
2. Uso de la herramienta `buscar_memoria`: Si el contexto pre-cargado está vacío, es incompleto o genera dudas para responder con precisión, invoca la herramienta `buscar_memoria` reformulando la consulta con los términos más relevantes antes de dar una respuesta definitiva.
3. Honestidad: Si tras consultar la memoria no existe información sobre el tema, indícalo amablemente sin inventar ni asumir datos.
</memory_guidelines>
"""


