POST http://127.0.0.1:8000/chat
Content-Type: application/json
{"user_input": "mcpB"}
HTTP 200
[Asserts]
body contains "data: {\"content\": \"Voy a buscar MCP\"}"
body contains "data: {\"content\": \"Respuesta no prevista: No relevant MCP server was found in the catalog.\"}"
body contains "data: [DONE]"