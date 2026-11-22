import axios from 'axios';

// API Configuration
const API_BASE_URL = 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod';

// Types
export interface AuthResponse {
  success: boolean;
  tokens: {
    access_token: string;
    id_token: string;
    refresh_token: string;
  };
}

export interface TicketValidationResponse {
  success: boolean;
  eligible?: boolean;
  ticket?: any;
  customer?: any;
  available_upgrades?: UpgradeTier[];
  eligibility_reasons?: string;
  error?: string;
}

export interface UpgradeTier {
  name: string;
  description: string;
  features: string[];
  tier: string;
  price: number;
}

export interface PricingResponse {
  success: boolean;
  pricing?: {
    base_price: number;
    upgrade_price: number;
    total_price: number;
    tier: string;
    date: string;
  };
  error?: string;
}

export interface RecommendationsResponse {
  success: boolean;
  recommendations?: UpgradeTier[];
  reasoning?: string;
  error?: string;
}

export interface TiersResponse {
  success: boolean;
  tiers?: UpgradeTier[];
  error?: string;
}

export interface UpgradeOption {
  id: string;
  name: string;
  price: number;
  features: string[];
  description: string;
}

export interface ChatResponse {
  success: boolean;
  response?: string;
  upgradeOptions?: UpgradeOption[];
  showUpgradeButtons?: boolean;
  error?: string;
}

export interface ChatRequest {
  message: string;
  conversationHistory?: any[];
  context?: any;
}

// API Service Class
class ApiService {
  private accessToken: string | null = null;

  constructor() {
    // Load token from localStorage if available and not expired
    const storedToken = localStorage.getItem('access_token');
    if (storedToken && this.isTokenValid(storedToken)) {
      this.accessToken = storedToken;
    } else {
      // Clear expired token
      localStorage.removeItem('access_token');
      this.accessToken = null;
    }
  }

  private isTokenValid(token: string): boolean {
    try {
      // Decode JWT token to check expiration
      const parts = token.split('.');
      if (parts.length !== 3) return false;
      
      const payload = JSON.parse(atob(parts[1]));
      const currentTime = Math.floor(Date.now() / 1000);
      
      // Check if token expires within next 5 minutes (300 seconds buffer)
      return payload.exp && payload.exp > (currentTime + 300);
    } catch (error) {
      console.error('Token validation error:', error);
      return false;
    }
  }

  private getHeaders() {
    const headers: any = {
      'Content-Type': 'application/json',
    };

    // Always check token validity before using it
    if (this.accessToken && this.isTokenValid(this.accessToken)) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    } else {
      // Token is expired or invalid, clear it
      this.logout();
    }

    return headers;
  }

  // Authentication
  async authenticate(email: string, password: string): Promise<AuthResponse> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/auth`,
        { email, password }
      );

      const authData = response.data as AuthResponse;
      
      if (authData.success && authData.tokens) {
        this.accessToken = authData.tokens.access_token;
        localStorage.setItem('access_token', this.accessToken);
      }

      return authData;
    } catch (error: any) {
      console.error('Authentication error:', error);
      return {
        success: false,
        tokens: { access_token: '', id_token: '', refresh_token: '' }
      };
    }
  }

  // Logout
  logout() {
    this.accessToken = null;
    localStorage.removeItem('access_token');
  }

  // Check if authenticated
  isAuthenticated(): boolean {
    return !!(this.accessToken && this.isTokenValid(this.accessToken));
  }

  // Ticket Validation
  async validateTicket(ticketId: string, upgradeTier: string): Promise<TicketValidationResponse> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/tickets/${ticketId}/validate`,
        { upgrade_tier: upgradeTier },
        { headers: this.getHeaders() }
      );

      return response.data as TicketValidationResponse;
    } catch (error: any) {
      console.error('Ticket validation error:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Validation failed'
      };
    }
  }

  // Pricing Calculation
  async calculatePricing(ticketId: string, upgradeTier: string, travelDate: string): Promise<PricingResponse> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/tickets/${ticketId}/pricing`,
        { upgrade_tier: upgradeTier, travel_date: travelDate },
        { headers: this.getHeaders() }
      );

      return response.data as PricingResponse;
    } catch (error: any) {
      console.error('Pricing calculation error:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Pricing calculation failed'
      };
    }
  }

  // Get Recommendations
  async getRecommendations(ticketId: string, customerId: string): Promise<RecommendationsResponse> {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/tickets/${ticketId}/recommendations?customer_id=${customerId}`,
        { headers: this.getHeaders() }
      );

      return response.data as RecommendationsResponse;
    } catch (error: any) {
      console.error('Recommendations error:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to get recommendations'
      };
    }
  }

  // Get Available Tiers
  async getAvailableTiers(ticketId: string): Promise<TiersResponse> {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/tickets/${ticketId}/tiers`,
        { headers: this.getHeaders() }
      );

      return response.data as TiersResponse;
    } catch (error: any) {
      console.error('Tiers error:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to get tiers'
      };
    }
  }
  // Chat with AI Agent
  async sendChatMessage(message: string, conversationHistory?: any[], context?: any): Promise<ChatResponse> {
    try {
      // Check token validity before making request
      if (!this.isAuthenticated()) {
        return {
          success: false,
          error: 'Authentication required. Please log in again.'
        };
      }

      const response = await axios.post(
        `${API_BASE_URL}/chat`,
        { 
          message, 
          conversationHistory: conversationHistory || [],
          context: context || {}
        },
        { headers: this.getHeaders() }
      );

      return response.data as ChatResponse;
    } catch (error: any) {
      console.error('Chat error:', error);
      
      // Handle 401 errors by clearing token and requiring re-authentication
      if (error.response?.status === 401) {
        this.logout();
        return {
          success: false,
          error: 'Session expired. Please log in again.'
        };
      }
      
      return {
        success: false,
        error: error.response?.data?.error || 'Chat failed'
      };
    }
  }
}

// Export singleton instance
export const apiService = new ApiService();