export class ChatService {
    constructor() {
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.apiUrl = isLocal && window.location.port === '3000' 
            ? 'http://127.0.0.1:8000/api/chat' 
            : '/api/chat';
    }

    async sendMessageStream(message, history, onToken) {
        try {
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message, history: history })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                fullText += chunk;
                if (onToken) {
                    onToken(chunk);
                }
            }
            return fullText;
        } catch (error) {
            console.error("Could not connect to the AI Backend:", error);
            const fallback = "I'm sorry, my systems are currently offline. Please ensure the Python backend server is running!";
            if (onToken) onToken(fallback);
            return fallback;
        }
    }
}
