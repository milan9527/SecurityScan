import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/api';
import './TicketUpgradeInterface.css';

interface Message {
  id: string;
  content: string;
  sender: 'customer' | 'ai';
  timestamp: Date;
  upgradeOptions?: UpgradeOption[];
  showUpgradeButtons?: boolean;
}

interface UpgradeOption {
  id: string;
  name: string;
  price: number;
  features: string[];
  description: string;
}

const TicketUpgradeInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [conversationContext, setConversationContext] = useState<{
    hasTicketInfo?: boolean;
    ticketId?: string;
    upgradeOptions?: UpgradeOption[];
    hasUpgradeOptions?: boolean;
  }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initial AI greeting
    addAIMessage("Hi! I'm your AI ticket assistant. I can help you upgrade your tickets, check pricing, and answer any questions. What can I help you with today?");
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const addAIMessage = (content: string, upgradeOptions?: UpgradeOption[], showUpgradeButtons?: boolean) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      content,
      sender: 'ai',
      timestamp: new Date(),
      upgradeOptions,
      showUpgradeButtons
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const addCustomerMessage = (content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      content,
      sender: 'customer',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const processNaturalLanguage = async (message: string) => {
    try {
      // Convert frontend message format to backend expected format
      const conversationHistory = messages.slice(-5).map(msg => ({
        role: msg.sender === 'customer' ? 'user' : 'assistant',
        content: msg.content
      }));

      // Call the real AI chat endpoint
      const chatResponse = await apiService.sendChatMessage(
        message, 
        conversationHistory, // Properly formatted conversation history
        conversationContext
      );
      
      if (chatResponse.success && chatResponse.response) {
        // Update conversation context if AI provided upgrade options
        if (chatResponse.upgradeOptions) {
          setConversationContext(prev => ({ 
            ...prev, 
            upgradeOptions: chatResponse.upgradeOptions, 
            hasUpgradeOptions: true 
          }));
        }
        
        // Check if the AI response indicates successful ticket validation
        // Look for ticket ID patterns in the AI response and update context
        const ticketIdMatch = chatResponse.response.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
        if (ticketIdMatch && chatResponse.showUpgradeButtons) {
          const extractedTicketId = ticketIdMatch[1];
          setConversationContext(prev => ({ 
            ...prev, 
            hasTicketInfo: true, 
            ticketId: extractedTicketId 
          }));
        }
        
        return {
          response: chatResponse.response,
          upgradeOptions: chatResponse.upgradeOptions,
          showUpgradeButtons: chatResponse.showUpgradeButtons
        };
      } else {
        // Fallback to basic responses if AI fails
        return await processBasicNaturalLanguage(message);
      }
    } catch (error) {
      console.error('AI chat error:', error);
      // Fallback to basic responses
      return await processBasicNaturalLanguage(message);
    }
  };

  const processBasicNaturalLanguage = async (message: string) => {
    const lowerMessage = message.toLowerCase();
    
    // Check if customer is asking about upgrades and has provided ticket info
    if ((lowerMessage.includes('upgrade') || lowerMessage.includes('better') || lowerMessage.includes('premium')) 
        && (lowerMessage.includes('ticket') || conversationContext.hasTicketInfo)) {
      
      try {
        // Use real API to get upgrade options
        const ticketId = conversationContext.ticketId || '550e8400-e29b-41d4-a716-446655440002';
        const tiersResponse = await apiService.getAvailableTiers(ticketId);
        
        if (tiersResponse.success && tiersResponse.tiers) {
          const upgradeOptions: UpgradeOption[] = tiersResponse.tiers.map(tier => ({
            id: tier.tier,
            name: tier.name,
            price: tier.price,
            features: tier.features,
            description: tier.description
          }));

          setConversationContext(prev => ({ ...prev, upgradeOptions, hasUpgradeOptions: true }));
          
          return {
            response: "Great! I found some upgrade options for your ticket. Based on what you're looking for, here are the available upgrades. Each option builds on your current ticket with additional benefits:",
            upgradeOptions,
            showUpgradeButtons: true
          };
        } else {
          return {
            response: "I'm having trouble loading upgrade options right now. Let me try to help you in another way. Could you tell me more about what kind of upgrade experience you're looking for?"
          };
        }
      } catch (error) {
        return {
          response: "I'm experiencing some technical difficulties accessing upgrade options. In the meantime, I can tell you that we typically offer Standard, Premium, and VIP upgrade tiers. Would you like me to explain what each includes?"
        };
      }
    }

    // Check if customer mentioned ticket ID or wants to see tickets
    if (lowerMessage.includes('ticket') && (lowerMessage.includes('550e8400') || lowerMessage.includes('my ticket') || lowerMessage.includes('show'))) {
      const ticketId = '550e8400-e29b-41d4-a716-446655440002';
      setConversationContext(prev => ({ ...prev, hasTicketInfo: true, ticketId }));
      
      try {
        // Try to validate the ticket to get details
        const validationResponse = await apiService.validateTicket(ticketId, 'standard');
        
        if (validationResponse.success && validationResponse.ticket) {
          return {
            response: `I can see your ticket (${ticketId}). It's a ${validationResponse.ticket.ticket_type || 'Standard'} ticket for ${validationResponse.ticket.original_price || '75.00'} with an event date coming up. Would you like to explore upgrade options to enhance your experience?`
          };
        } else {
          return {
            response: `I can see your ticket (${ticketId}). It's a Standard ticket for $75.00 with an event date coming up. Would you like to explore upgrade options to enhance your experience?`
          };
        }
      } catch (error) {
        return {
          response: `I can see your ticket (${ticketId}). It's a Standard ticket for $75.00 with an event date coming up. Would you like to explore upgrade options to enhance your experience?`
        };
      }
    }

    // General responses based on keywords
    if (lowerMessage.includes('price') || lowerMessage.includes('cost') || lowerMessage.includes('how much')) {
      return {
        response: "I can help you with pricing! Upgrade costs vary depending on the tier you choose. To give you accurate pricing, could you tell me your ticket ID or let me know which type of upgrade interests you most?"
      };
    }

    if (lowerMessage.includes('help') || lowerMessage.includes('what can you do')) {
      return {
        response: "I can help you with: ✓ Checking your ticket details ✓ Showing available upgrade options ✓ Calculating upgrade pricing ✓ Processing upgrades ✓ Answering questions about features and benefits. Just tell me what you'd like to do!"
      };
    }

    // Default response
    return {
      response: "I understand you're interested in ticket services. To better assist you, could you share your ticket ID or tell me what specific help you need? I can check upgrade options, pricing, or answer any questions you have."
    };
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = inputMessage.trim();
    
    // Check if user is providing a ticket ID and update context
    const ticketIdMatch = userMessage.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
    if (ticketIdMatch) {
      const extractedTicketId = ticketIdMatch[1];
      setConversationContext(prev => ({ 
        ...prev, 
        hasTicketInfo: true, 
        ticketId: extractedTicketId 
      }));
    }
    
    addCustomerMessage(userMessage);
    setInputMessage('');
    setIsTyping(true);

    try {
      // Process the message with natural language understanding
      const aiResponse = await processNaturalLanguage(userMessage);
      
      setTimeout(() => {
        addAIMessage(aiResponse.response, aiResponse.upgradeOptions, aiResponse.showUpgradeButtons);
        setIsTyping(false);
      }, 1000);

    } catch (error) {
      setTimeout(() => {
        addAIMessage("I'm sorry, I'm having trouble processing your request right now. Please try again.");
        setIsTyping(false);
      }, 1000);
    }
  };

  const handleUpgradeSelection = async (option: UpgradeOption) => {
    addCustomerMessage(`I'd like the ${option.name} upgrade`);
    setIsTyping(true);

    try {
      // Use the chat endpoint instead of the pricing endpoint to avoid CORS issues
      const chatResponse = await apiService.sendChatMessage(
        `I want to proceed with the ${option.name} upgrade for $${option.price}. Please help me complete this upgrade.`,
        messages.slice(-3).map(msg => ({
          role: msg.sender === 'customer' ? 'user' : 'assistant',
          content: msg.content
        })), // Last 3 messages for context - properly formatted
        {
          ...conversationContext,
          selectedUpgrade: {
            id: option.id,
            name: option.name,
            price: option.price,
            features: option.features
          }
        }
      );
      
      setTimeout(() => {
        if (chatResponse.success && chatResponse.response) {
          addAIMessage(chatResponse.response, chatResponse.upgradeOptions, chatResponse.showUpgradeButtons);
        } else {
          // Fallback response if chat fails
          addAIMessage(`Excellent choice! The ${option.name} for $${option.price} includes: ${option.features.join(', ')}. To complete this upgrade, I'll need to process the payment and update your ticket. Would you like me to proceed with the payment processing?`);
        }
        setIsTyping(false);
      }, 1000);
    } catch (error) {
      setTimeout(() => {
        // Fallback response if there's an error
        addAIMessage(`Excellent choice! The ${option.name} for $${option.price} includes: ${option.features.join(', ')}. To complete this upgrade, I'll need to process the payment and update your ticket. Would you like me to proceed with the payment processing?`);
        setIsTyping(false);
      }, 1000);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>🤖 AI Ticket Assistant</h2>
        <p>Chat naturally about your ticket upgrades</p>
      </div>

      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.sender}`}>
            <div className="message-bubble">
              <div className="message-content">{message.content}</div>
              
              {message.showUpgradeButtons && message.upgradeOptions && (
                <div className="upgrade-options">
                  {message.upgradeOptions.map((option) => (
                    <div key={option.id} className="upgrade-card">
                      <div className="upgrade-header">
                        <h4>{option.name}</h4>
                        <span className="upgrade-price">${option.price}</span>
                      </div>
                      <p className="upgrade-description">{option.description}</p>
                      <ul className="upgrade-features">
                        {option.features.map((feature, idx) => (
                          <li key={idx}>✓ {feature}</li>
                        ))}
                      </ul>
                      <button 
                        className="select-upgrade-btn"
                        onClick={() => handleUpgradeSelection(option)}
                      >
                        Select {option.name}
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="message-time">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="message ai">
            <div className="message-bubble typing">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div className="typing-text">AI is typing...</div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <div className="input-container">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Type your message here... (e.g., 'I want to upgrade my ticket')"
            disabled={isTyping}
          />
          <button 
            onClick={handleSendMessage}
            disabled={isTyping || !inputMessage.trim()}
            className="send-btn"
          >
            Send
          </button>
        </div>
        
        <div className="chat-hints">
          <p>💡 Try saying: "Show me my ticket" • "I want to upgrade" • "What are my options?" • "How much does it cost?"</p>
        </div>
      </div>
    </div>
  );
};

export default TicketUpgradeInterface;