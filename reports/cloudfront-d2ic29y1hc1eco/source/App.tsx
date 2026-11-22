import React, { useState, useEffect } from 'react';
import './App.css';
import { apiService } from './services/api';
import LoginForm from './components/LoginForm';
import TicketUpgradeInterface from './components/TicketUpgradeInterface';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check if user is already authenticated with valid token
    setIsAuthenticated(apiService.isAuthenticated());
  }, []);

  // Listen for authentication state changes
  useEffect(() => {
    const checkAuthStatus = () => {
      const authStatus = apiService.isAuthenticated();
      if (authStatus !== isAuthenticated) {
        setIsAuthenticated(authStatus);
        if (!authStatus) {
          setError('Session expired. Please log in again.');
        }
      }
    };

    // Check auth status every 30 seconds
    const interval = setInterval(checkAuthStatus, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleLogin = async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiService.authenticate(email, password);
      
      if (response.success) {
        setIsAuthenticated(true);
      } else {
        setError('Authentication failed. Please check your credentials.');
      }
    } catch (error) {
      setError('Authentication error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    apiService.logout();
    setIsAuthenticated(false);
    setError(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎫 Ticket Upgrade System</h1>
        <p>Powered by AgentCore AI</p>
        {isAuthenticated && (
          <button onClick={handleLogout} className="logout-btn">
            Logout
          </button>
        )}
      </header>

      <main className="App-main">
        {!isAuthenticated ? (
          <LoginForm 
            onLogin={handleLogin} 
            isLoading={isLoading} 
            error={error} 
          />
        ) : (
          <TicketUpgradeInterface />
        )}
      </main>

      <footer className="App-footer">
        <p>Demo: Real-time connection to deployed AgentCore agents</p>
      </footer>
    </div>
  );
}

export default App;
