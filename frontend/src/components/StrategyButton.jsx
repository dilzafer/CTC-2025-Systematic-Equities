/**
 * StrategyButton Component
 *
 * Reusable button component for executing trading strategies.
 * Features: Loading states, color coding, success/error feedback.
 */

import { useState } from 'react';
import './StrategyButton.css';

const StrategyButton = ({ label, onClick, variant = 'default', disabled = false }) => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState(''); // 'success' or 'error'

  const handleClick = async () => {
    if (disabled || loading) return;

    setLoading(true);
    setMessage('');
    setMessageType('');

    try {
      await onClick();
      setMessage('Success!');
      setMessageType('success');

      // Clear success message after 3 seconds
      setTimeout(() => {
        setMessage('');
        setMessageType('');
      }, 3000);
    } catch (error) {
      setMessage(error.message || 'Failed');
      setMessageType('error');

      // Clear error message after 5 seconds
      setTimeout(() => {
        setMessage('');
        setMessageType('');
      }, 5000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="strategy-button-container">
      <button
        className={`strategy-button strategy-button-${variant} ${loading ? 'loading' : ''} ${disabled ? 'disabled' : ''}`}
        onClick={handleClick}
        disabled={disabled || loading}
      >
        {loading ? 'Running...' : label}
      </button>
      {message && (
        <span className={`strategy-message ${messageType}`}>
          {message}
        </span>
      )}
    </div>
  );
};

export default StrategyButton;
