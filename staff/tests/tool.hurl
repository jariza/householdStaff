POST http://127.0.0.1:8000/chat
Content-Type: application/json
{"user_input": "tool"}
HTTP 200
[Asserts]
body contains "data: {\"content\": \"Delego el encendido de luz al jardinero.\"}"
body contains "data: {\"content\": \"Respuesta no prevista: Tarea derivada al gardener: 'encender luz jardin'\"}"
body contains "data: {\"content\": \"El jardinero ha dicho cosas.\"}"
body contains "data: [DONE]"
