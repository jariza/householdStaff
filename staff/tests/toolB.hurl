POST http://127.0.0.1:8000/chat
Content-Type: application/json
{"user_input": "toolB"}
HTTP 200
[Asserts]
body contains "data: {\"content\": \"Voy a ejecutar la herramienta como butler\"}"
body contains "data: {\"content\": \"Respuesta no prevista: The lights in the 'zoneBUTLER' area of the garden are turned on.\"}"
body contains "data: [DONE]"
