import React, { useState } from 'react';
import './LoginForm.css';

interface LoginFormProps {
  onLogin: (email: string, password: string) => void;
  isLoading: boolean;
  error: string | null;
}

const LoginForm: React.FC<LoginFormProps> = ({ onLogin, isLoading, error }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLogin(email, password);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2>🔐 Login to Ticket System</h2>
        <p className="login-subtitle">Connect to AgentCore AI Agents</p>
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
              placeholder="Enter your email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              placeholder="Enter your password"
            />
          </div>

          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}

          <button 
            type="submit" 
            className="login-btn"
            disabled={isLoading}
          >
            {isLoading ? '🔄 Authenticating...' : '🚀 Login'}
          </button>
        </form>

        <div className="demo-info">
          <h3>🧪 Demo Credentials</h3>
          <p><strong>Email:</strong> testuser@example.com</p>
          <p><strong>Password:</strong> TempPass123!</p>
          <small>Or use any valid Cognito user credentials</small>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;