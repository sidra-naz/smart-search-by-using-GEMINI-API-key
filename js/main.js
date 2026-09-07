import { ChatbotState } from './ChatbotState.js';
import { ChatService } from './ChatService.js';
import { ChatbotUI } from './ChatbotUI.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the application architecture
    const state = new ChatbotState();
    const service = new ChatService();
    const ui = new ChatbotUI(state, service);
    
    // Expose toggle globally if needed by other site elements
    window.toggleATVChatbot = () => ui.toggleChat();
});
