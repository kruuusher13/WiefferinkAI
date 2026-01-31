/**
 * GarageAI Executive Command Center - Client v3.0
 *
 * Carbon Obsidian Theme with:
 * - The Pulse (center audio visualizer)
 * - Thinking Widget (tool call logging)
 * - Command bar with /persona support
 */

const STATUS = {
    OFFLINE: 'OFFLINE',
    CONNECTING: 'CONNECTING...',
    ONLINE: 'HARRY ACTIVE',
    THINKING: 'PROCESSING...'
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
        this.isThinking = false;
        this.analyser = null;
        this.visualizerInterval = null;
    }

    // Logging helper for the Thinking Widget
    log(message, type = 'info') {
        const logContainer = document.getElementById('thinkingLog');
        const now = new Date();
        const timeStr = now.toTimeString().slice(0, 8);

        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = `
            <span class="log-time">${timeStr}</span>
            <span class="log-content ${type}">${message}</span>
        `;
        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Update UI state
    setStatus(status) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const thinkingBadge = document.getElementById('thinkingBadge');
        const pulseCore = document.getElementById('pulseCore');
        const pulseLabel = document.getElementById('pulseLabel');
        const pulseIcon = document.getElementById('pulseIcon');
        const visualizer = document.getElementById('visualizer');

        statusText.textContent = status;

        switch (status) {
            case STATUS.OFFLINE:
                statusDot.className = 'status-dot';
                thinkingBadge.textContent = 'IDLE';
                thinkingBadge.style.color = '#71717a';
                pulseCore.className = 'pulse-core';
                pulseLabel.textContent = 'Click to Connect';
                pulseIcon.style.display = 'block';
                visualizer.style.display = 'none';
                break;
            case STATUS.CONNECTING:
                statusDot.className = 'status-dot';
                thinkingBadge.textContent = 'CONNECTING';
                thinkingBadge.style.color = '#ffb100';
                pulseLabel.textContent = 'Connecting...';
                break;
            case STATUS.ONLINE:
                statusDot.className = 'status-dot online';
                thinkingBadge.textContent = 'LISTENING';
                thinkingBadge.style.color = '#10b981';
                pulseCore.className = 'pulse-core listening';
                pulseLabel.textContent = 'Listening';
                pulseIcon.style.display = 'none';
                visualizer.style.display = 'flex';
                break;
            case STATUS.THINKING:
                statusDot.className = 'status-dot thinking';
                thinkingBadge.textContent = 'THINKING';
                thinkingBadge.style.color = '#ffb100';
                pulseCore.className = 'pulse-core thinking';
                pulseLabel.textContent = 'Processing...';
                break;
        }
    }

    async init() {
        const commandInput = document.getElementById('commandInput');
        const sendBtn = document.getElementById('sendBtn');

        this.setStatus(STATUS.CONNECTING);
        this.log('Initiating WebSocket connection...');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/web`;
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = async () => {
            this.log('WebSocket connected', 'result');
            this.log('Initializing audio contexts...');
            this.setStatus(STATUS.ONLINE);
            this.isConnected = true;
            commandInput.disabled = false;
            sendBtn.disabled = false;

            await this.initAudioContexts();
            await this.startAudioCapture();
            this.startVisualizer();

            // Initial DB fetch
            this.fetchTable('customers');
            this.log('System ready. Harry is listening.', 'result');
        };

        this.socket.onmessage = async (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'audio') {
                this.playAudioChunk(data.audio);
            }

            if (data.type === 'transcript') {
                this.addTranscript(data.role, data.text);
                if (data.role === 'user') {
                    this.log(`User: "${data.text}"`, 'user');
                } else {
                    this.log(`Harry: "${data.text.slice(0, 60)}..."`, 'result');
                    this.setStatus(STATUS.ONLINE);
                }
            }

            // Tool call events (when backend sends them)
            if (data.type === 'tool_call') {
                this.setStatus(STATUS.THINKING);
                this.log(`Calling tool: ${data.name}`, 'tool');
                if (data.args) {
                    this.log(`  Args: ${JSON.stringify(data.args)}`, 'tool');
                }
            }

            if (data.type === 'tool_result') {
                this.log(`Result: ${data.result.slice(0, 80)}...`, 'result');
            }
        };

        this.socket.onclose = () => {
            this.log('Connection closed', 'error');
            this.setStatus(STATUS.OFFLINE);
            this.isConnected = false;
            commandInput.disabled = true;
            sendBtn.disabled = true;
            this.stopAudioCapture();
            this.stopVisualizer();
        };

        this.socket.onerror = (err) => {
            this.log(`WebSocket error: ${err.message || 'Unknown error'}`, 'error');
        };
    }

    async initAudioContexts() {
        try {
            this.captureContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: CAPTURE_SAMPLE_RATE });
            this.playbackContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: PLAYBACK_SAMPLE_RATE });
            this.nextStartTime = this.playbackContext.currentTime;
            this.log('Audio contexts initialized (16kHz in, 24kHz out)');
        } catch (err) {
            this.log(`AudioContext init failed: ${err.message}`, 'error');
        }
    }

    addTranscript(role, text) {
        const container = document.getElementById('transcriptMessages');
        const msgDiv = document.createElement('div');
        msgDiv.className = `transcript-msg ${role}`;
        msgDiv.textContent = text;
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
    }

    sendMessage(text) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;

        // Check for /persona command
        if (text.startsWith('/persona ')) {
            const prompt = text.slice(9).trim();
            if (prompt) {
                this.log(`Injecting persona: "${prompt.slice(0, 40)}..."`, 'tool');
                this.socket.send(JSON.stringify({ type: 'update_prompt', prompt }));
                this.addTranscript('user', `[Persona Update] ${prompt}`);
            }
            return;
        }

        this.addTranscript('user', text);
        this.log(`Sending text: "${text}"`, 'user');
        this.socket.send(JSON.stringify({ type: 'text', text }));
        this.setStatus(STATUS.THINKING);
    }

    setLanguage(lang) {
        this.currentLanguage = lang;
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.log(`Language switch: ${lang.toUpperCase()}`, 'tool');
            this.socket.send(JSON.stringify({ type: 'set_language', value: lang }));
        }
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        });
    }

    injectPrompt(prompt) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.log(`Applying instruction: "${prompt.slice(0, 40)}..."`, 'tool');
            this.socket.send(JSON.stringify({ type: 'update_prompt', prompt }));
        }
    }

    async startAudioCapture() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { channelCount: 1, sampleRate: CAPTURE_SAMPLE_RATE, echoCancellation: true }
            });

            this.input = this.captureContext.createMediaStreamSource(stream);
            this.processor = this.captureContext.createScriptProcessor(4096, 1, 1);

            // Create analyser for visualizer
            this.analyser = this.captureContext.createAnalyser();
            this.analyser.fftSize = 64;
            this.input.connect(this.analyser);

            this.processor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);
                const pcmData = this.floatTo16BitPCM(inputData);
                if (this.socket?.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify({ type: 'audio', data: this.arrayBufferToBase64(pcmData) }));
                }
            };

            this.input.connect(this.processor);
            this.processor.connect(this.captureContext.destination);
            this.log('Microphone capture started');
        } catch (err) {
            this.log(`Microphone error: ${err.message}`, 'error');
        }
    }

    startVisualizer() {
        if (!this.analyser) return;

        const bars = document.querySelectorAll('.visualizer-bar');
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

        this.visualizerInterval = setInterval(() => {
            this.analyser.getByteFrequencyData(dataArray);
            bars.forEach((bar, i) => {
                const value = dataArray[i * 2] || 0;
                const height = Math.max(8, (value / 255) * 50);
                bar.style.height = `${height}px`;
            });
        }, 50);
    }

    stopVisualizer() {
        if (this.visualizerInterval) {
            clearInterval(this.visualizerInterval);
            this.visualizerInterval = null;
        }
    }

    stopAudioCapture() {
        this.processor?.disconnect();
        this.input?.disconnect();
        this.analyser?.disconnect();
        this.captureContext?.close();
        this.playbackContext?.close();
        this.stopVisualizer();
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
        } catch (err) {
            this.log(`Audio playback error: ${err.message}`, 'error');
        }
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
        } catch (err) {
            console.error('DB Fetch failed:', err);
        }
    }

    renderTable(data) {
        const head = document.getElementById('tableHead');
        const body = document.getElementById('tableBody');
        head.innerHTML = '';
        body.innerHTML = '';

        if (!data || data.length === 0) {
            body.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #71717a;">No data available</td></tr>';
            return;
        }

        const cols = Object.keys(data[0]);
        cols.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            head.appendChild(th);
        });

        data.forEach(row => {
            const tr = document.createElement('tr');
            cols.forEach(col => {
                const td = document.createElement('td');
                td.textContent = row[col] ?? '-';
                tr.appendChild(td);
            });
            body.appendChild(tr);
        });
    }
}

// Global client instance
let client = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Pulse click to connect
    const pulseCore = document.getElementById('pulseCore');
    pulseCore.addEventListener('click', () => {
        if (!client || !client.isConnected) {
            client = new GarageAIClient();
            client.init();
        }
    });

    // Command input
    const commandInput = document.getElementById('commandInput');
    const sendBtn = document.getElementById('sendBtn');

    commandInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && commandInput.value.trim()) {
            client?.sendMessage(commandInput.value.trim());
            commandInput.value = '';
        }
    });

    sendBtn.addEventListener('click', () => {
        if (commandInput.value.trim()) {
            client?.sendMessage(commandInput.value.trim());
            commandInput.value = '';
        }
    });

    // Language buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => client?.setLanguage(btn.dataset.lang));
    });

    // Prompt injection
    document.getElementById('applyPrompt').addEventListener('click', () => {
        const prompt = document.getElementById('promptInput').value;
        client?.injectPrompt(prompt);
    });

    // Database tabs
    document.querySelectorAll('.data-tab').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.data-tab').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            client?.fetchTable(e.target.dataset.table);
        });
    });

    // Refresh button
    document.getElementById('refreshDb').addEventListener('click', () => {
        const activeTable = document.querySelector('.data-tab.active').dataset.table;
        client?.fetchTable(activeTable);
    });

    // Controls sidebar toggle
    const controlsToggle = document.getElementById('controlsToggle');
    const controlsSidebar = document.getElementById('controlsSidebar');
    controlsToggle.addEventListener('click', () => {
        controlsSidebar.classList.toggle('open');
    });

    // Initial table fetch
    if (!client) {
        fetch('/api/db/customers')
            .then(res => res.json())
            .then(data => {
                const tempClient = { renderTable: GarageAIClient.prototype.renderTable };
                tempClient.renderTable(data);
            })
            .catch(() => {});
    }
});
