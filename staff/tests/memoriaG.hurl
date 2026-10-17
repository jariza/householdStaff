POST http://127.0.0.1:8000/chat
Content-Type: application/json
{"user_input": "memoriaG"}
HTTP 200
[Asserts]
body contains "data: {\"content\": \"Solicito al jardinero actualizar su memoria.\"}"
body contains "data: {\"content\": \"Respuesta no prevista: Tarea derivada al gardener: 'actualizar memoria'\"}"
body contains "data: {\"content\": \"El jardinero ha dicho cosas.\"}"
body contains "data: [DONE]"
