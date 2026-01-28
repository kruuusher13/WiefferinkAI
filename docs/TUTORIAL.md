# Tutorial: Running GarageAI with Vapi.ai

This specific tutorial guides you through running the GarageAI backend locally, exposing it via a tunnel, connecting it to Vapi.ai, and testing it with a real phone call.

## Prerequisites

1.  **Python 3.10+** installed.
2.  **Google Gemini API Key** (for the LLM).
3.  **Vapi.ai Account** (for the voice interface).
4.  **Ngrok** (or similar) to expose your local server to the internet.

---

## Step 1: Local Setup

1.  **Clone/Navigate** to the project folder:
    ```bash
    cd /path/to/GarageAI
    ```
    

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Environment Variables**:
    You need to set your Google API Key.
    ```bash
    export GOOGLE_API_KEY="AIzaSyDgQ46mmboKJu-ucGvgkk6lqERgOKiO-YE"
    ```
    *(On Windows PowerShell: `$env:GOOGLE_API_KEY="your_key"`)*

4.  **Run the Server**:
    Start the FastAPI backend.
    ```bash
    python main.py
    ```
    You should see output indicating the server is running on `http://0.0.0.0:8000`.

---

## Step 2: Expose to the Internet

Vapi.ai needs a public URL to send audio data (transcribed text) to your agent. We will use **ngrok**.

1.  **Install ngrok** (if you haven't): [https://ngrok.com/download](https://ngrok.com/download)
2.  **Start a Tunnel**:
    Open a new terminal window and run:
    ```bash
    ngrok http 8000
    ```
3.  **Copy the URL**:
    Look for the "Forwarding" line, e.g., `https://a1b2-c3d4.ngrok-free.app`.
    *Copy this URL. This is your public endpoint.*

---

## Step 3: Configure Vapi.ai

1.  **Log in** to your [Vapi Dashboard](https://dashboard.vapi.ai/).
2.  **Create a New Assistant**:
    *   Name: `GarageAI Architect`
    *   Transcriber: `Deepgram` (Dutch language recommended if available, or set language to Dutch).
    *   Model: You can leave this default, but we will be overriding the logic with our "Server URL".
    *   Voice: Choose a Dutch voice (e.g., from ElevenLabs or Azure within Vapi).
3.  **Set Server URL**:
    In the Assistant settings, find **"Server URL"** (or Callback URL).
    *   Enter your ngrok URL appended with `/chat`.
    *   Example: `https://a1b2-c3d4.ngrok-free.app/chat`
4.  **Save** the Assistant.

---

## Step 4: Phone Connection

1.  **Get a Phone Number**:
    *   In Vapi Dashboard, go to **Phone Numbers**.
    *   Buy or assign a trial number.
    *   **Attach** your `GarageAI Architect` assistant to this phone number.

---

## Step 5: Test the Call

1.  **Pick up your Mobile Phone**.
2.  **Dial** the number assigned in Step 4.
3.  **Speak**:
    *   *Agent*: "Goedemiddag..." (Or whatever your System Prompt greeting implies, though Vapi might handle the initial 'Hello').
    *   *You*: "Is mijn auto met kenteken XX-99-XX al klaar?"
4.  **Observe**:
    *   Check your **Local Terminal** running `main.py`. You should see logs like:
        ```text
        INFO:GarageAI:Received message for call ...: Is mijn auto met kenteken XX-99-XX al klaar?
        INFO:GarageAI:Response for call ...: Werkorder #2024-501 voor kenteken XX-99-XX staat op status: 'Wacht op onderdelen'.
        ```
    *   *Agent (Voice)*: Should speak the response back to you in Dutch.

## Step 6: Database Setup (Real SQL)

We use a Dockerized SQL Server to mimic the real WinCar database.

1.  **Start Database**:
    ```bash
    docker-compose up -d
    ```
2.  **Initialize Schema & Data**:
    ```bash
    python init_db.py
    ```
    *This creates tables (Work Orders, Customers) and inserts dummy data like "Jan de Vries" and vehicle "XX-99-XX".*

3.  **Verify**:
    You can query the DB directly:
    ```bash
    docker exec -it wincar_sql /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P StrongPassword123! -Q "SELECT * FROM WinCarLive.dbo.Werkplaats_Werkorders"
    ```

## Troubleshooting

-   **500 Errors in ngrok**: Check your `main.py` terminal for Python errors.
-   **No Voice**: Ensure Vapi is set to handle "Server" mode correctly and that your API key is valid.
-   **Wrong Language**: Ensure the Voice selected in Vapi is a Dutch voice, otherwise it will try to read Dutch text with an English accent.
-   **Vapi Latency**: If the call drops due to silence, ensure `main.py` is using the StreamingResponse implementation.


export GOOGLE_API_KEY="AIzaSyDtT1KNU7gn0gsi2y-6y5Gde9K6tOAzVmA" && ./start_all.sh