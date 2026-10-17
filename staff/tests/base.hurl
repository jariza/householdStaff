POST http://127.0.0.1:8000/chat
Content-Type: application/json
{"user_input": "base"}
HTTP 200
[Asserts]
body contains "data: {\"content\": \"Respuestas sin que intervengan otros agentes.\"}"
body contains "data: [DONE]"