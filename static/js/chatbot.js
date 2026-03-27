/**
 * AI Shopping Assistant Chatbot Widget
 * Professional chatbot interface for e-commerce
 */

class ShoppingChatbot {
    constructor(options = {}) {
        this.apiEndpoint = options.apiEndpoint || '/chatbot/api/chat/';
        this.sessionId = options.sessionId || null;
        this.isOpen = false;
        this.isTyping = false;
        this.messages = [];
        
        this.init();
    }
    
    init() {
        this.createWidget();
        this.attachEventListeners();
        this.showWelcomeMessage();
    }
    
    createWidget() {
        // Create toggle button
        const toggle = document.createElement('button');
        toggle.className = 'chatbot-toggle';
        toggle.id = 'chatbot-toggle';
        toggle.innerHTML = `
            <svg class="chatbot-toggle-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                <path d="M7 9h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2z"/>
            </svg>
            <span class="chatbot-toggle-badge" id="chatbot-badge">1</span>
        `;
        
        // Create chat window
        const window = document.createElement('div');
        window.className = 'chatbot-window';
        window.id = 'chatbot-window';
        window.innerHTML = `
            <div class="chatbot-header">
                <div class="chatbot-avatar">🛍️</div>
                <div class="chatbot-info">
                    <div class="chatbot-name">Shopping Assistant</div>
                    <div class="chatbot-status">
                        <span class="chatbot-status-dot"></span>
                        <span>Online • Ready to help</span>
                    </div>
                </div>
                <button class="chatbot-close" id="chatbot-close">
                    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            </div>
            <div class="chatbot-messages" id="chatbot-messages"></div>
            <div class="chatbot-input-area">
                <div class="chatbot-input-container">
                    <textarea 
                        class="chatbot-input" 
                        id="chatbot-input" 
                        placeholder="Ask me anything about products, orders, or shopping..."
                        rows="1"
                    ></textarea>
                    <button class="chatbot-send" id="chatbot-send">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(toggle);
        document.body.appendChild(window);
        
        this.toggleBtn = toggle;
        this.chatWindow = window;
        this.messagesContainer = document.getElementById('chatbot-messages');
        this.input = document.getElementById('chatbot-input');
        this.sendBtn = document.getElementById('chatbot-send');
    }
    
    attachEventListeners() {
        // Toggle button
        this.toggleBtn.addEventListener('click', () => this.toggle());
        
        // Close button
        document.getElementById('chatbot-close').addEventListener('click', () => this.close());
        
        // Send button
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Input events
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.input.addEventListener('input', () => {
            this.autoResizeInput();
        });
        
        // Close on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        this.isOpen = true;
        this.chatWindow.classList.add('open');
        this.toggleBtn.classList.add('active');
        this.input.focus();
        this.hideBadge();
    }
    
    close() {
        this.isOpen = false;
        this.chatWindow.classList.remove('open');
        this.toggleBtn.classList.remove('active');
    }
    
    showBadge(count = 1) {
        const badge = document.getElementById('chatbot-badge');
        badge.textContent = count;
        badge.classList.add('show');
    }
    
    hideBadge() {
        const badge = document.getElementById('chatbot-badge');
        badge.classList.remove('show');
    }
    
    autoResizeInput() {
        this.input.style.height = 'auto';
        this.input.style.height = Math.min(this.input.scrollHeight, 100) + 'px';
    }
    
    showWelcomeMessage() {
        const welcomeHtml = `
            <div class="chat-welcome">
                <div class="chat-welcome-icon">👋</div>
                <div class="chat-welcome-title">Hi! I'm your Shopping Assistant</div>
                <div class="chat-welcome-text">
                    I can help you find products, track orders, answer questions, and more!
                </div>
                <div class="chat-quick-replies">
                    <button class="chat-quick-reply" data-message="Show me trending products">🔥 Trending</button>
                    <button class="chat-quick-reply" data-message="What are your return policies?">📦 Returns</button>
                    <button class="chat-quick-reply" data-message="Track my order">🚚 Track Order</button>
                    <button class="chat-quick-reply" data-message="Show my cart">🛒 My Cart</button>
                </div>
            </div>
        `;
        
        this.messagesContainer.innerHTML = welcomeHtml;
        
        // Attach quick reply handlers
        this.messagesContainer.querySelectorAll('.chat-quick-reply').forEach(btn => {
            btn.addEventListener('click', () => {
                const message = btn.dataset.message;
                this.input.value = message;
                this.sendMessage();
            });
        });
    }
    
    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isTyping) return;
        
        // Clear input
        this.input.value = '';
        this.autoResizeInput();
        
        // Add user message
        this.addMessage('user', message);
        
        // Show typing indicator
        this.showTyping();
        
        try {
            const response = await this.callAPI(message);
            this.hideTyping();
            this.handleResponse(response);
            
            // Store session ID
            if (response.session_id) {
                this.sessionId = response.session_id;
            }
        } catch (error) {
            this.hideTyping();
            this.addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
            console.error('Chatbot error:', error);
        }
    }
    
    async callAPI(message) {
        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error('API request failed');
        }
        
        return response.json();
    }
    
    getCSRFToken() {
        // Try to get from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        // Try to get from meta tag
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }
    
    handleResponse(response) {
        const { type, message, data } = response;
        
        switch (type) {
            case 'product_list':
                this.addMessage('assistant', message);
                if (data && data.products) {
                    this.addProductCards(data.products);
                }
                break;
                
            case 'cart':
                this.addMessage('assistant', message);
                if (data && data.cart) {
                    this.addCartDisplay(data.cart);
                }
                break;
                
            case 'order':
                if (data && data.success !== false) {
                    this.addMessage('assistant', message);
                    this.addOrderDisplay(data);
                } else {
                    this.addMessage('assistant', message || data.message);
                }
                break;
                
            case 'order_list':
                this.addMessage('assistant', message);
                if (data && data.orders) {
                    this.addOrdersList(data.orders);
                }
                break;
                
            case 'cart_action':
                this.addMessage('assistant', message || (data && data.message));
                break;
                
            case 'size_recommendation':
                this.addMessage('assistant', message);
                break;
                
            case 'faq':
                this.addMessage('assistant', message);
                break;
                
            case 'error':
                this.addMessage('assistant', message || 'An error occurred');
                break;
                
            default:
                this.addMessage('assistant', message || 'I\'m here to help!');
        }
        
        // Add quick replies for follow-up
        this.addQuickReplies(type);
    }
    
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        
        const avatar = role === 'user' ? '👤' : '🛍️';
        
        // Convert markdown-like formatting
        content = this.formatMessage(content);
        
        messageDiv.innerHTML = `
            <div class="chat-message-avatar">${avatar}</div>
            <div class="chat-message-content">${content}</div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        this.messages.push({ role, content });
    }
    
    formatMessage(content) {
        if (!content) return '';
        
        // Bold text
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Line breaks
        content = content.replace(/\n/g, '<br>');
        
        return content;
    }
    
    addProductCards(products) {
        const container = document.createElement('div');
        container.className = 'chat-products';
        
        products.slice(0, 4).forEach(product => {
            const card = document.createElement('div');
            card.className = 'chat-product-card';
            card.innerHTML = `
                <img 
                    class="chat-product-image" 
                    src="${product.image_url || ''}" 
                    alt="${product.name}"
                    onerror="this.style.display='none'"
                >
                <div class="chat-product-info">
                    <div class="chat-product-name">${product.name}</div>
                    <div class="chat-product-price">
                        <span class="chat-product-price-current">₹${product.price.toLocaleString()}</span>
                        ${product.compare_price ? `<span class="chat-product-price-old">₹${product.compare_price.toLocaleString()}</span>` : ''}
                        ${product.discount_percentage ? `<span class="chat-product-badge discount">-${product.discount_percentage}%</span>` : ''}
                    </div>
                    <div class="chat-product-actions">
                        <a href="/product/${product.slug}/" class="chat-product-btn secondary">View</a>
                        <button class="chat-product-btn primary" data-product-id="${product.id}">Add to Cart</button>
                    </div>
                </div>
            `;
            
            // Add to cart handler
            card.querySelector('.chat-product-btn.primary').addEventListener('click', (e) => {
                e.preventDefault();
                this.input.value = `Add product ${product.id} to cart`;
                this.sendMessage();
            });
            
            container.appendChild(card);
        });
        
        this.messagesContainer.appendChild(container);
        this.scrollToBottom();
    }
    
    addCartDisplay(cart) {
        const container = document.createElement('div');
        container.className = 'chat-cart';
        
        if (cart.items.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280;">Your cart is empty</p>';
        } else {
            let html = '';
            cart.items.forEach(item => {
                html += `
                    <div class="chat-cart-item">
                        <span>${item.product_name} ${item.variant ? `(${item.variant})` : ''} × ${item.quantity}</span>
                        <span>₹${item.line_total.toLocaleString()}</span>
                    </div>
                `;
            });
            html += `
                <div class="chat-cart-total">
                    <span>Total (${cart.total_items} items)</span>
                    <span>₹${cart.subtotal.toLocaleString()}</span>
                </div>
            `;
            container.innerHTML = html;
        }
        
        this.messagesContainer.appendChild(container);
        this.scrollToBottom();
    }
    
    addOrderDisplay(order) {
        const container = document.createElement('div');
        container.className = 'chat-order';
        
        const statusClass = order.status.toLowerCase();
        
        container.innerHTML = `
            <div class="chat-order-header">
                <span class="chat-order-number">${order.order_number}</span>
                <span class="chat-order-status ${statusClass}">${order.status_display}</span>
            </div>
            <div style="font-size: 13px; color: #6b7280; margin-bottom: 8px;">
                Order placed: ${order.created_at}
            </div>
            ${order.tracking_number ? `
                <div style="font-size: 13px; margin-bottom: 8px;">
                    📦 Tracking: <strong>${order.tracking_number}</strong>
                    ${order.carrier ? `(${order.carrier})` : ''}
                </div>
            ` : ''}
            <div style="font-size: 14px; font-weight: 600; margin-top: 8px;">
                Total: ₹${order.total_amount.toLocaleString()}
            </div>
        `;
        
        this.messagesContainer.appendChild(container);
        this.scrollToBottom();
    }
    
    addOrdersList(orders) {
        const container = document.createElement('div');
        container.className = 'chat-products';
        
        orders.forEach(order => {
            const statusClass = order.status.toLowerCase();
            const card = document.createElement('div');
            card.className = 'chat-product-card';
            card.style.padding = '12px';
            card.innerHTML = `
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-weight: 600; color: #667eea;">${order.order_number}</span>
                        <span class="chat-order-status ${statusClass}" style="font-size: 11px; padding: 2px 8px;">${order.status_display}</span>
                    </div>
                    <div style="font-size: 13px; color: #6b7280;">${order.created_at} • ${order.items_count} items</div>
                    <div style="font-size: 14px; font-weight: 600; margin-top: 4px;">₹${order.total_amount.toLocaleString()}</div>
                </div>
            `;
            
            card.style.cursor = 'pointer';
            card.addEventListener('click', () => {
                this.input.value = `Track order ${order.order_number}`;
                this.sendMessage();
            });
            
            container.appendChild(card);
        });
        
        this.messagesContainer.appendChild(container);
        this.scrollToBottom();
    }
    
    addQuickReplies(responseType) {
        let replies = [];
        
        switch (responseType) {
            case 'product_list':
                replies = [
                    { text: '🔍 More like these', message: 'Show similar products' },
                    { text: '💰 Cheaper options', message: 'Show cheaper options' },
                    { text: '🛒 Add to cart', message: 'Add the first one to cart' }
                ];
                break;
            case 'cart':
                replies = [
                    { text: '🛒 Checkout', message: 'Proceed to checkout' },
                    { text: '🛍️ Continue shopping', message: 'Show me more products' }
                ];
                break;
            case 'order':
            case 'order_list':
                replies = [
                    { text: '🛍️ Shop more', message: 'Show trending products' },
                    { text: '❓ Help', message: 'What can you help me with?' }
                ];
                break;
            default:
                return;
        }
        
        if (replies.length === 0) return;
        
        const container = document.createElement('div');
        container.className = 'chat-quick-replies';
        container.style.marginTop = '12px';
        
        replies.forEach(reply => {
            const btn = document.createElement('button');
            btn.className = 'chat-quick-reply';
            btn.textContent = reply.text;
            btn.addEventListener('click', () => {
                this.input.value = reply.message;
                this.sendMessage();
            });
            container.appendChild(btn);
        });
        
        this.messagesContainer.appendChild(container);
        this.scrollToBottom();
    }
    
    showTyping() {
        this.isTyping = true;
        this.sendBtn.disabled = true;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message assistant';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="chat-message-avatar">🛍️</div>
            <div class="chat-message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        this.sendBtn.disabled = false;
        
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.shoppingChatbot = new ShoppingChatbot();
});
