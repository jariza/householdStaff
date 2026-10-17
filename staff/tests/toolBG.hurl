POST http://127.0.0.1:8000/chat
Content-Type: application/json
{"user_input": "toolBG"}
HTTP 200
[Asserts]
body contains "data: {\"content\": \"Caso mixto de herrmienta butler\"}"
body contains "data: {\"content\": \"Respuesta no prevista: The lights in the 'zoneBUTLERMIXTO' area of the garden are turned on.\"}"
body contains "data: [DONE]"
