# 🏰 Household Staff AI (Pet Project)

A hands-on, experimental sandbox currently built to understand **LLMs, multi-agent orchestrations, long-term memory consolidation, RAG, and custom tooling** from the ground up—without relying on high-level pre-cooked "turnkey" agent frameworks. 

As I explore the ecosystem, I'll keep adding whatever catches my attention and feels worth investigating (for example, **MCP** is already sitting high on my TODO list).

---

## 💡 About This Project

### Why this project exists
This is a personal **pet project** created as a learning space. The goal is to learn how core mechanics work under the hood using state-graph primitives (LangGraph, FastAPI, and Server-Sent Events) rather than getting stuck relying strictly on off-the-shelf wrappers.

### Written with AI Assistance (Not "Vibecoded")
This codebase was developed with the assistance of AI as a pair-programming partner. However, **this is explicitly not a "vibecoded" project** where code was blindly pasted without care. Every component—from state propagation to memory routing and tool injection—was crafted deliberately to understand *how* and *why* it works. 

*(Full disclosure: this README file itself was 100% written by an AI to summarize my chaotic notes and codebase!)*

### Expect Continuous Iteration (and Creative Disorder!)
Because this is built in spare time between daily life and personal commitments, development happens asynchronously. Ideas are implemented as they come, so expect active `TODO` comments, temporary debug hacks, loose `print()` statements, and occasional refactoring scattered across the codebase!

---

## 🏛️ System Components

The application models a domestic household staff architecture:
- **Telegram Receiver (`tgRecv`)**: The primary user interface layer. Handles interactions via Telegram Bot API, streaming back concatenated SSE (Server-Sent Events) responses from the backend while managing Telegram message limits and security filtering.
- **Telegram Notifier (`tgNotif`)**: Outbound notification module used to trigger automated alerts or async messages directly to the user over Telegram.
- **FastAPI Core (`staff`)**: Houses the central state graph and agent network.
- **Butler Agent**: The primary interface and orchestrator. Evaluates incoming user requests and either fulfills them directly or delegates them to domain specialists.
- **Specialist Agents (e.g., Gardener)**: Domain-specific agents running isolated subgraphs with their own local toolsets and memory loops.
- **Memory Consolidator**: An asynchronous background system analyzing 24-hour interaction windows to extract, structure, and save long-term persistent memory without cluttering short-term state.
- **Custom Extensibility**: Dynamic discovery for custom tools and agents under `./staff/agents/custom/` and `./staff/tools/custom/`.

---

## 🚀 Getting Started

### 1. Prerequisites & Environment Setup

Ensure you have **Python 3.10+** installed.

#### Step 1: Clone and set up virtual environment
```bash
cd householdStaff
python3 -m venv venv
source venv/bin/activate
```

#### Step 2: Install dependencies
Each module manages its dependencies. Install all required packages:
```bash
pip install -r staff/requirements.txt
pip install -r tgRecv/requirements.txt
pip install -r tgNotif/requirements.txt
```

#### Step 3: Configure Environment Variables & Tool Mappings
Copy the provided `.env.dist` templates to `.env` in each respective folder, and set up the optional tool configuration template:

```bash
cp staff/.env.dist staff/.env
cp staff/agents_tools.yaml.dist staff/agents_tools.yaml
cp tgRecv/.env.dist tgRecv/.env
cp tgNotif/.env.dist tgNotif/.env
```

1. **`staff/.env`**:
   - `DEBUG`: Set to `true` for offline testing or `false` to use live LLMs.
   - `GOOGLE_API_KEY`: Your Gemini API key (required when `DEBUG=false`).
   - `LOCAL_OLLAMA_URL`: URL for local Ollama service (e.g., `http://localhost:11434`), used for background memory deduplication and merging via `qwen2.5:1.5b`.
   - `NOTIFIER_URL`: Webhook URL for outbound notifications (e.g., `http://127.0.0.1:8001/notify`).
   - `STORE_EMBEDDINGS_MODEL`: FastEmbed model name (e.g., `sentence-transformers/all-MiniLM-L6-v2`).

2. **`tgRecv/.env`**:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token from `@BotFather`.
   - `ALLOWED_USER_ID`: Your numeric Telegram User ID for authorization.
   - `BUTLER_API_URL`: Backend endpoint URL (e.g., `http://127.0.0.1:8000/chat`).

3. **`tgNotif/.env`**:
   - `TELEGRAM_BOT_TOKEN`: Same Telegram Bot API token.
   - `DESTINATION_CHAT_ID`: Telegram Chat ID where notifications should be sent.

---

## 🛠️ Execution Modes

The core application (`staff`) supports two distinct execution modes controlled via the `DEBUG` environment variable in `staff/.env`.

### 1. Debug Mode (`DEBUG=true`)
* **Purpose**: Local testing without external API dependency or token cost.
* **Engine**: Uses `DebugEngine`, which responds with pre-determined responses based on keyword triggers (`base`, `jardinero`, `tool`, `memoriaB`, `memoriaG`, etc.).
* **Storage**: Volatile in-memory store (`InMemorySaver` and `InMemoryStore`).

### 2. Gemini / Live Mode (`DEBUG=false`)
* **Purpose**: Full agent orchestration using Google's Gemini models.
* **Engine**: Uses `LLMEngine` with multi-tier model fallbacks (`gemini-3.6-flash`, `gemini-3.5-flash`, etc. for Butler, and lighter flash models for specialists).
* **Storage**: Persistent SQLite databases (`langgraph_checkpoint.db` for execution threads, `langgraph_store.db` for long-term vector-backed store).
* **Background Processing**: Integrates with local Ollama running `qwen2.5:1.5b` to automatically consolidate and merge long-term memories without blocking conversation turns.

---

## 🏃 Running the Application

To run the complete system, start the services in separate terminal sessions:

#### Step 1: Start Ollama (Required for Memory Merging in Live Mode)
Ensure Ollama is running with the required model:
```bash
ollama run qwen2.5:1.5b
```

#### Step 2: Start Core Backend (`staff`)
```bash
cd staff
uvicorn main:app --reload --port 8000
```

#### Step 3: Start Telegram Outbound Notifier (`tgNotif`)
```bash
cd tgNotif
uvicorn main:app --reload --port 8001
```

#### Step 4: Start Telegram Bot Receiver (`tgRecv`)
```bash
cd tgRecv
python main.py
```

---

## 📡 API Endpoints Summary

The backend (`staff`) exposes several core FastAPI routes:

* **`POST /chat`**: Main SSE streaming endpoint for user interactions with the Butler graph.
* **`POST /alert`**: Endpoint for background/scheduled triggers. Allows proactive notifications sent directly via `tgNotif`.
* **`POST /consolidate-memory`**: Triggers the `MemoryConsolidator` agent to analyze past conversations (>24h) and extract persistent long-term memories.
* **`GET|PUT|DELETE /store/*`**: Full CRUD interface for inspecting and managing the underlying long-term vector store.

---

## 🧩 Extending Agents & Tools

Adding new capabilities is modular and requires zero changes to core graph files:

* **Custom Agents**: Drop a Python module in `./staff/agents/custom/` with a class inheriting from `BaseAgent` and implementing a `process()` method. It will be dynamically registered and accessible via delegation.
* **Custom Tools**: Place tool modules inside `./staff/tools/custom/`.
* **Dynamic Tool Mapping (`agents_tools.yaml`)**: You can dynamically attach custom tools to specific agents using `staff/agents_tools.yaml` (see `staff/agents_tools.yaml.dist` for reference):
  ```yaml
  butler:
    - custom_weather_tool
  gardener:
    - custom_irrigation_tool
  ```

## 🙈 Elephant in the Room (Technical Debt)

Yes, I know...
- Yes, I know this project is screaming for Docker containers and `docker compose`.
- Yes, I know there are values in the code that should be living in config files.
- Yes, I know I'm mixing python code and system prompts in the same place.

I'll get around to refactoring all of that at some point... I suppose!