export class ChatbotState {
    constructor() {
        this.isOpen = false;
        this.isTyping = false;
        this.messages = [];
        this.sessions = [];
        this.currentSessionId = null;
        
        this.loadSessions();
    }

    loadSessions() {
        const saved = localStorage.getItem('atvChatSessions');
        if (saved) {
            try {
                this.sessions = JSON.parse(saved);
            } catch(e) {
                this.sessions = [];
            }
        }
        
        if (this.sessions.length > 0) {
            this.currentSessionId = this.sessions[0].id;
            this.messages = this.sessions[0].messages || [];
        } else {
            this.createNewSession();
        }
    }

    saveSessions() {
        localStorage.setItem('atvChatSessions', JSON.stringify(this.sessions));
    }

    createNewSession() {
        const newSession = {
            id: Date.now().toString(),
            title: "New Chat",
            messages: [],
            timestamp: new Date().toISOString()
        };
        // Add to front
        this.sessions.unshift(newSession);
        this.currentSessionId = newSession.id;
        this.messages = newSession.messages;
        this.saveSessions();
        return newSession;
    }

    switchSession(id) {
        const session = this.sessions.find(s => s.id === id);
        if (session) {
            this.currentSessionId = id;
            this.messages = session.messages || [];
            return true;
        }
        return false;
    }
    
    deleteSession(id) {
        this.sessions = this.sessions.filter(s => s.id !== id);
        
        if (this.currentSessionId === id) {
            if (this.sessions.length > 0) {
                this.currentSessionId = this.sessions[0].id;
                this.messages = this.sessions[0].messages || [];
            } else {
                this.createNewSession();
            }
        }
        this.saveSessions();
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        return this.isOpen;
    }

    addMessage(sender, text) {
        const message = {
            id: Date.now(),
            sender, // 'user' or 'bot'
            text,
            timestamp: new Date().toISOString()
        };
        this.messages.push(message);
        
        // Update current session
        const currentSession = this.sessions.find(s => s.id === this.currentSessionId);
        if (currentSession) {
            currentSession.messages = this.messages;
            
            // Set title based on first user message if title is still "New Chat"
            if (sender === 'user' && currentSession.title === "New Chat") {
                currentSession.title = text.substring(0, 30) + (text.length > 30 ? "..." : "");
            }
            
            // Move current session to top of list
            this.sessions = this.sessions.filter(s => s.id !== this.currentSessionId);
            this.sessions.unshift(currentSession);
            
            this.saveSessions();
        }
        
        return message;
    }
    
    // Allows updating a message text progressively (for streaming)
    updateLastMessageText(text) {
        if (this.messages.length > 0) {
            this.messages[this.messages.length - 1].text = text;
            this.saveSessions();
        }
    }

    setTyping(status) {
        this.isTyping = status;
        return this.isTyping;
    }

    getMessages() {
        return this.messages;
    }
    
    getSessions() {
        return this.sessions;
    }

    clearMessages() {
        this.messages = [];
        const currentSession = this.sessions.find(s => s.id === this.currentSessionId);
        if (currentSession) {
            currentSession.messages = [];
            this.saveSessions();
        }
    }
}
