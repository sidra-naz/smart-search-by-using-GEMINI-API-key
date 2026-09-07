export class ChatbotUI {
    constructor(state, service) {
        this.state = state;
        this.service = service;
        this.cacheDOM();
        this.bindEvents();
        
        // Initial render
        this.renderHistoryList();
        this.loadSessionMessages();
    }

    cacheDOM() {
        this.chatForm = document.getElementById('chat-form');
        this.chatInput = document.getElementById('chat-input');
        this.messagesContainer = document.getElementById('chat-messages');
        
        this.mobileMenuBtn = document.getElementById('mobile-menu-btn');
        this.sidebar = document.getElementById('sidebar');
        this.sidebarOverlay = document.getElementById('sidebar-overlay');
        
        // Desktop Sidebar Toggles
        this.sidebarCloseBtn = document.getElementById('sidebar-close-btn');
        this.sidebarOpenBtn = document.getElementById('sidebar-open-btn');
        
        // New chat button
        this.newChatBtn = document.getElementById('new-chat-btn');
        
        // History list container
        this.historyList = document.getElementById('chat-history-list');
        
        // Auto-focus input on load
        if (this.chatInput) this.chatInput.focus();
    }

    bindEvents() {
        if (this.chatForm) {
            this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        }
        
        // Add Enter to submit support (without shift)
        if (this.chatInput) {
            this.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSubmit(e);
                }
            });
        }

        // Mobile Sidebar Toggle
        if (this.mobileMenuBtn && this.sidebar && this.sidebarOverlay) {
            this.mobileMenuBtn.addEventListener('click', () => this.toggleSidebarMobile());
            this.sidebarOverlay.addEventListener('click', () => this.closeSidebarMobile());
        }

        // Desktop Sidebar Toggle
        if (this.sidebarCloseBtn && this.sidebarOpenBtn && this.sidebar) {
            this.sidebarCloseBtn.addEventListener('click', () => this.toggleSidebarDesktop(false));
            this.sidebarOpenBtn.addEventListener('click', () => this.toggleSidebarDesktop(true));
        }

        // New Chat
        if (this.newChatBtn) {
            this.newChatBtn.addEventListener('click', () => this.startNewChat());
        }
    }

    startNewChat() {
        this.state.createNewSession();
        this.loadSessionMessages();
        this.renderHistoryList();
        this.closeSidebarMobile(); // Close sidebar if on mobile
        
        if (this.chatInput) this.chatInput.focus();
    }

    loadSessionMessages() {
        this.messagesContainer.innerHTML = '';
        const messages = this.state.getMessages();
        
        if (messages.length === 0) {
            // Add initial greeting if empty
            const msg = this.state.addMessage('bot', "Hi there! I'm your ATV & Buggy Adventure Guide. How can I help you plan your next off-road experience?");
            this.renderMessage(msg);
        } else {
            // Render existing messages
            messages.forEach(msg => this.renderMessage(msg));
        }
        this.scrollToBottom();
    }

    renderHistoryList() {
        if (!this.historyList) return;
        this.historyList.innerHTML = '';
        
        const sessions = this.state.getSessions();
        sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'sidebar__history-item';
            if (session.id === this.state.currentSessionId) {
                item.classList.add('active');
            }
            
            const titleSpan = document.createElement('span');
            titleSpan.textContent = session.title;
            titleSpan.style.overflow = 'hidden';
            titleSpan.style.textOverflow = 'ellipsis';
            titleSpan.style.whiteSpace = 'nowrap';
            item.appendChild(titleSpan);
            
            // Delete button
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'delete-btn';
            deleteBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';
            deleteBtn.title = "Delete chat";
            
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent triggering the switchSession click
                this.state.deleteSession(session.id);
                this.renderHistoryList();
                this.loadSessionMessages();
            });
            
            item.appendChild(deleteBtn);
            
            item.addEventListener('click', () => {
                if (session.id !== this.state.currentSessionId) {
                    this.state.switchSession(session.id);
                    this.loadSessionMessages();
                    this.renderHistoryList();
                    this.closeSidebarMobile();
                }
            });
            
            this.historyList.appendChild(item);
        });
    }

    toggleSidebarDesktop(open) {
        if (open) {
            this.sidebar.classList.remove('sidebar--collapsed');
            this.sidebarOpenBtn.classList.add('hidden');
        } else {
            this.sidebar.classList.add('sidebar--collapsed');
            this.sidebarOpenBtn.classList.remove('hidden');
        }
    }

    toggleSidebarMobile() {
        this.sidebar.classList.toggle('sidebar--open');
        this.sidebarOverlay.classList.toggle('active');
    }

    closeSidebarMobile() {
        this.sidebar.classList.remove('sidebar--open');
        this.sidebarOverlay.classList.remove('active');
    }

    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    getAvatarSVG(sender) {
        if (sender === 'bot') {
            return `<img src="assets/images.jpg" alt="A&B Logo" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
        }
        return `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;
    }

    getSenderName(sender) {
        return sender === 'bot' ? 'ATVBot' : 'You';
    }

    renderMessage(message) {
        const messageEl = document.createElement('div');
        messageEl.className = `message message--${message.sender}`;
        
        messageEl.innerHTML = `
            <div class="message__avatar">
                ${this.getAvatarSVG(message.sender)}
            </div>
            <div class="message__content-wrapper">
                <div class="message__sender-name">${this.getSenderName(message.sender)}</div>
                <div class="message__bubble">${this.escapeHTML(message.text)}</div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageEl);
        this.scrollToBottom();
        return messageEl;
    }

    renderTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message message--bot';
        indicator.id = 'typing-indicator-container';
        
        indicator.innerHTML = `
            <div class="message__avatar">
                ${this.getAvatarSVG('bot')}
            </div>
            <div class="message__content-wrapper">
                <div class="message__sender-name">ATVBot</div>
                <div class="message__bubble">
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(indicator);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator-container');
        if (indicator) {
            indicator.remove();
        }
    }

    scrollToBottom() {
        // Scroll the parent container, not just the messages div
        const container = this.messagesContainer.parentElement;
        container.scrollTop = container.scrollHeight;
    }

    formatMessageText(str, isStreaming = false) {
        if (!str) return '';

        let textToFormat = str;

        if (isStreaming) {
            // While actively streaming, temporarily hide trailing incomplete markdown image syntax
            // so we don't attempt to load partial/broken image URLs on micro-token chunks.
            textToFormat = textToFormat.replace(/!\[[^\]]*\]\([^)]*$/g, '');
            textToFormat = textToFormat.replace(/!\[[^\]]*$/g, '');
        }
        
        // Basic HTML escaping to prevent XSS
        let formatted = textToFormat.replace(/&/g, '&amp;')
                                   .replace(/</g, '&lt;')
                                   .replace(/>/g, '&gt;')
                                   .replace(/"/g, '&quot;')
                                   .replace(/'/g, '&#39;');

        const fallbackImg = "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7953?alt=media&token=d2268693-7d38-4e82-b21a-74b5a682ba98";

        // Helper to construct image HTML
        const buildImgHTML = (rawUrl, alt) => {
            const cleanUrl = rawUrl.replace(/&amp;/g, '&');
            return `<div class="vehicle-card-img-wrapper" style="margin: 12px 0;"><img src="${cleanUrl}" alt="${alt}" style="max-width: 100%; max-height: 260px; border-radius: 12px; object-fit: cover; display: block; box-shadow: 0 4px 14px rgba(0,0,0,0.18);" onerror="this.onerror=null; this.src='${fallbackImg}';"></div>`;
        };

        // Parse FULL COMPLETE markdown images: ![alt](url)
        formatted = formatted.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s\)]+)\)/g, (match, alt, url) => {
            return buildImgHTML(url, alt || "Vehicle Preview");
        });

        // Parse markdown bold: **text**
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // New lines to <br>
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }


    escapeHTML(str) {
        return this.formatMessageText(str);
    }

    async handleSubmit(e) {
        if (e && e.preventDefault) e.preventDefault();
        
        const text = this.chatInput.value.trim();
        if (!text || this.state.isTyping) return;
        
        // Clear input
        this.chatInput.value = '';
        
        // Add user message
        const userMsg = this.state.addMessage('user', text);
        this.renderMessage(userMsg);
        
        // Set typing state
        this.state.setTyping(true);
        this.renderTypingIndicator();
        
        // Build history excluding the latest user message which is passed in 'text'
        const messages = this.state.getMessages();
        const historyToSend = messages.slice(0, -1).map(m => ({
            role: m.sender === 'bot' ? 'assistant' : 'user',
            content: m.text
        }));

        // Get bot response
        try {
            let botMsg = null;
            let messageEl = null;
            let bubbleEl = null;
            let renderPending = false;

            await this.service.sendMessageStream(text, historyToSend, (chunk) => {
                // Initialize message on the very first chunk
                if (!botMsg) {
                    this.removeTypingIndicator();
                    botMsg = this.state.addMessage('bot', '');
                    messageEl = this.renderMessage(botMsg);
                    bubbleEl = messageEl.querySelector('.message__bubble');
                }
                
                botMsg.text += chunk;
                this.state.updateLastMessageText(botMsg.text);

                // Smooth batched DOM updates at 60fps using requestAnimationFrame
                if (!renderPending) {
                    renderPending = true;
                    requestAnimationFrame(() => {
                        if (bubbleEl && botMsg) {
                            bubbleEl.innerHTML = this.formatMessageText(botMsg.text, true);
                            this.scrollToBottom();
                        }
                        renderPending = false;
                    });
                }
            });
            
            // Final render after stream completes
            if (bubbleEl && botMsg) {
                bubbleEl.innerHTML = this.formatMessageText(botMsg.text, false);
                this.scrollToBottom();
            }

            // Re-render history list in case the title was updated by the first message
            this.renderHistoryList();
            
            // Fallback in case the stream ended with zero chunks
            if (!botMsg) {
                this.removeTypingIndicator();
            }
            
        } catch (error) {
            console.error('Failed to send message:', error);
            this.removeTypingIndicator();
            const errorMsg = this.state.addMessage('bot', "Sorry, I'm having trouble connecting right now. Please try again later.");
            this.renderMessage(errorMsg);
        } finally {
            this.state.setTyping(false);
        }
    }
}
