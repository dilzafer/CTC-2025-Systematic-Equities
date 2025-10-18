/**
 * StatusIndicator Component
 *
 * Shows active strategies and arbitrage status.
 */

import './StatusIndicator.css';

const StatusIndicator = ({ runningStrategies, arbitrageRunning, connected }) => {
  return (
    <div className="status-indicator">
      <div className="status-row">
        <span className="status-label">Server Connection:</span>
        <span className={`status-badge ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>

      <div className="status-row">
        <span className="status-label">Arbitrage:</span>
        <span className={`status-badge ${arbitrageRunning ? 'running' : 'stopped'}`}>
          {arbitrageRunning ? '● Running' : '○ Stopped'}
        </span>
      </div>

      {runningStrategies.length > 0 && (
        <div className="status-row">
          <span className="status-label">Active Strategies:</span>
          <div className="running-strategies">
            {runningStrategies.map((strategy, index) => (
              <span key={index} className="strategy-tag">
                {strategy}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StatusIndicator;
