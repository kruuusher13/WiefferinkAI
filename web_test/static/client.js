// GarageAI WebSocket Client v2.2
// Supports: Voice (16kHz in, 24kHz out), Chat, Language Toggle, Transcriptions, DB Visualization, Prompt Injection

const STATUS = {
    DISCONNECTED: 'SYSTEM OFFLINE',
    CONNECTING: 'CONNECTING...',
    CONNECTED: 'SYSTEM ONLINE / HARRY ACTIVE'
};

const CAPTURE_SAMPLE_RATE = 16000;
const PLAYBACK_SAMPLE_RATE = 24000;

class GarageAIClient {
    constructor() {
        this.captureContext = null;
        this.playbackContext = null;
        this.socket = null;
        this.processor = null;
        this.input = null;
        this.nextStartTime = 0;
        this.currentLanguage = 'en';
        this.isConnected = false;
    }

    async init() {
        const startBtn = document.getElementById('startBtn');
        const statusText = document.getElementById('statusText');
        const connectionStatus = document.getElementById('connectionStatus');
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/web`;

        statusText.innerText = STATUS.CONNECTING;
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = async () => {
            console.log('WebSocket Connected');
            statusText.innerText = STATUS.CONNECTED;
            connectionStatus.classList.add('online');
            startBtn.disabled = true;
            startBtn.innerText = "🎧 Listening...";
            chatInput.disabled = false;
            sendBtn.disabled = false;
            this.isConnected = true;

            await this.initAudioContexts();
            await this.startAudioCapture();

            // Initial DB fetch
            this.fetchTable('customers');
        };

        this.socket.onmessage = async (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'audio') {
                this.playAudioChunk(data.audio);
            }

            if (data.type === 'transcript') {
                this.addMessage(data.role, data.text);
            }
        };

        this.socket.onclose = () => {
            statusText.innerText = STATUS.DISCONNECTED;
            connectionStatus.classList.remove('online');
            startBtn.disabled = false;
            startBtn.innerText = "🎤 Start Conversation";
            chatInput.disabled = true;
            sendBtn.disabled = true;
            this.isConnected = false;
            this.stopAudioCapture();
        };
    }

    async initAudioContexts() {
        try {
            this.captureContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: CAPTURE_SAMPLE_RATE });
            this.playbackContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: PLAYBACK_SAMPLE_RATE });
            this.nextStartTime = this.playbackContext.currentTime;
        } catch (err) {
            console.error('AudioContext init failed:', err);
        }
    }

    addMessage(role, text) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.innerText = text;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    sendTextMessage(text) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.addMessage('user', text);
            this.socket.send(JSON.stringify({ type: 'text', text }));
        }
    }

    injectPrompt(prompt) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.addMessage('assistant', `Applying dynamic instruction...`);
            this.socket.send(JSON.stringify({ type: 'update_prompt', prompt }));
        }
    }

    setLanguage(lang) {
        this.currentLanguage = lang;
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type: 'set_language', value: lang }));
        }
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        });
    }

    async startAudioCapture() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { channelCount: 1, sampleRate: CAPTURE_SAMPLE_RATE, echoCancellation: true }
            });

            this.input = this.captureContext.createMediaStreamSource(stream);
            this.processor = this.captureContext.createScriptProcessor(4096, 1, 1);

            this.processor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);
                const pcmData = this.floatTo16BitPCM(inputData);
                if (this.socket?.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify({ type: 'audio', data: this.arrayBufferToBase64(pcmData) }));
                }
            };

            this.input.connect(this.processor);
            this.processor.connect(this.captureContext.destination);
        } catch (err) {
            console.error('Mic capture failed:', err);
        }
    }

    stopAudioCapture() {
        this.processor?.disconnect();
        this.input?.disconnect();
        this.captureContext?.close();
        this.playbackContext?.close();
    }

    playAudioChunk(base64Data) {
        try {
            const binaryString = window.atob(base64Data);
            const int16Array = new Int16Array(new Uint8Array(binaryString.length).map((_, i) => binaryString.charCodeAt(i)).buffer);
            const float32Array = new Float32Array(int16Array.length).map((_, i) => int16Array[i] / 32768);
            const buffer = this.playbackContext.createBuffer(1, float32Array.length, PLAYBACK_SAMPLE_RATE);
            buffer.copyToChannel(float32Array, 0);
            const source = this.playbackContext.createBufferSource();
            source.buffer = buffer;
            source.connect(this.playbackContext.destination);
            if (this.nextStartTime < this.playbackContext.currentTime) this.nextStartTime = this.playbackContext.currentTime;
            source.start(this.nextStartTime);
            this.nextStartTime += buffer.duration;
        } catch (err) { console.error('Audio playback failed:', err); }
    }

    floatTo16BitPCM(input) {
        let output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            let s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output.buffer;
    }

    arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
        return window.btoa(binary);
    }

    async fetchTable(tableName) {
        try {
            const response = await fetch(`/api/db/${tableName}`);
            const data = await response.json();
            this.renderTable(data);
        } catch (err) { console.error('DB Fetch failed:', err); }
    }

    renderTable(data) {
        const head = document.getElementById('tableHead');
        const body = document.getElementById('tableBody');
        head.innerHTML = '';
        body.innerHTML = '';

        if (!data || data.length === 0) {
            body.innerHTML = '<tr><td colspan="5">No data available.</td></tr>';
            return;
        }

        const cols = Object.keys(data[0]);
        cols.forEach(col => {
            const th = document.createElement('th');
            th.innerText = col;
            head.appendChild(th);
        });

        data.forEach(row => {
            const tr = document.createElement('tr');
            cols.forEach(col => {
                const td = document.createElement('td');
                td.innerText = row[col];
                tr.appendChild(td);
            });
            body.appendChild(tr);
        });
    }
}

let client = null;

document.getElementById('startBtn').addEventListener('click', () => {
    client = new GarageAIClient();
    client.init();
});

document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => client?.setLanguage(btn.dataset.lang));
});

document.getElementById('updatePromptBtn').addEventListener('click', () => {
    const prompt = document.getElementById('promptInput').value;
    client?.injectPrompt(prompt);
});

document.querySelectorAll('.db-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.db-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        client?.fetchTable(e.target.dataset.table);
    });
});

document.getElementById('refreshDbBtn').addEventListener('click', () => {
    const activeTable = document.querySelector('.db-btn.active').dataset.table;
    client?.fetchTable(activeTable);
});

document.getElementById('chatInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
        client?.sendTextMessage(e.target.value);
        e.target.value = '';
    }
});

document.getElementById('sendBtn').addEventListener('click', () => {
    const input = document.getElementById('chatInput');
    if (input.value.trim()) {
        client?.sendTextMessage(input.value);
        input.value = '';
    }
});
