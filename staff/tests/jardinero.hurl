POST http://127.0.0.1:8000/chat
Content-Type: application/json
{"user_input": "jardinero"}
HTTP 200
[Asserts]
body contains "data: {\"content\": \"Voy a consultar este tema con el jardinero.\"}"
body contains "data: {\"content\": \"Respuesta no prevista: Tarea derivada al gardener: 'Consulta sobre el jard\\u00edn.'\"}"
body contains "data: {\"content\": \"El jardinero ha dicho cosas.\"}"
body contains "data: [DONE]"
