POST http://127.0.0.1:8000/chat
Content-Type: application/json
{"user_input": "memoriaB"}
HTTP 200
[Asserts]
body contains "data: {\"content\": \"Voy a actualizar la memoria\"}"
body contains "data: {\"content\": \"Respuesta no prevista: Memoria marcada para actualizar.\"}"
body contains "data: [DONE]"

