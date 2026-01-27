# WiefferinkAI / GarageAI

**GarageAI** is a voice-enabled AI assistant designed for Dutch garages using the WinCar management system. It integrates **FastAPI**, **LangGraph**, **Google Gemini**, and **Vapi.ai** to provide a seamless voice experience for checking work orders, stocks, and scheduling appointments.

## 🚀 Features

- **Voice Interface**: Powered by Vapi.ai for low-latency voice conversations.
- **Smart Agent**: Uses LangGraph and Google Gemini 2.0 Flash for intelligent reasoning.
- **WinCar Integration**: Connects to a SQL Server database to read/write garage data:
  - **Identify Customers**: Recognizes customers by phone number.
  - **Werkplaats (Workshop)**: Checks status of work orders.
  - **Magazijn (Warehouse)**: Checks part stock and pricing.
  - **Financieel (Finance)**: Generates payment links.
  - **Agenda**: Schedules appointments (Prototype).
- **Streaming Responses**: Implements Server-Sent Events (SSE) for real-time voice responses.
- **Robust Error Handling**: Automatically handles connectivity issues and LLM failures.

## 📋 Prerequisites

Before running the system, ensure you have the following installed:

- **Docker**: For running the SQL Server container.
- **Python 3.12+**: For the backend server.
- **Ngrok**: For exposing your local server to Vapi.ai.
- **Vapi.ai Account**: To configure the voice assistant.
- **Google AI Studio API Key**: For Gemini models.

## 🛠️ Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/kruuusher13/WiefferinkAI.git
    cd WiefferinkAI
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

1.  **Set Environment Variables**:
    You need a Google API Key. You can set it temporarily in your terminal:
    ```bash
    export GOOGLE_API_KEY="your_google_api_key_here"
    ```
    Or create a `.env` file (not monitored by git) if you implement `python-dotenv` loading.

## 🏃‍♂️ Usage

### 1. Start the System
We have provided a convenience script `start_all.sh` that checks for Docker, starts the database, and launches the server.

```bash
./start_all.sh
```

This script will:
- Check if the `wincar_sql` Docker container is running (and start it if needed).
- Wait for the database to be ready.
- Start the FastAPI server on `http://0.0.0.0:8000`.

### 2. Expose Local Server
In a separate terminal window, start Ngrok to tunnel your local port 8000 to the internet:

```bash
ngrok http 8000
```

Copy the simplified HTTPS URL provided by Ngrok (e.g., `https://random-name.ngrok-free.app`).

### 3. Configure Vapi.ai
1.  Go to the [Vapi Dashboard](https://dashboard.vapi.ai).
2.  Select or Create an Assistant.
3.  Set the **Server URL** to your Ngrok URL appended with `/chat`:
    ```
    https://<your-ngrok-url>/chat
    ```
4.  (Optional) Import `vapi_assistant_config.json` if you have specific voice settings.

## 🧪 Testing

### Local Logic Test
To test the agent logic without Vapi (Text-based):
```bash
python test_logic_cli.py
```

### Local Server Test
To simulate a Vapi request to your local server:
```bash
python test_local_server.py
```

### Database visualization
To see what is currently in the mock database:
```bash
python view_db.py
```

## 📂 Project Structure

- `main.py`: FastAPI application entry point, handles Vapi streams.
- `graph.py`: LangGraph definitions (Agent, Tools, State).
- `tools.py`: Python functions wrapping SQL queries for WinCar modules.
- `init_db.py`: Database initialization and seeding script.
- `mock_wincar_db.sql`: Schema and seed data for the mock SQL Server.

## ⚠️ Troubleshooting

- **llm-failed**: Check if your Ngrok tunnel is active and the URL found in the logs matches the one in Vapi. Also verify your `GOOGLE_API_KEY`.
- **Database Connection Error**: Ensure the Docker container `wincar_sql` is running (`docker ps`).
- **404 Not Found**: Ensure you added `/chat` to the end of your Ngrok URL in Vapi.

## 📄 License
Private/Proprietary.
