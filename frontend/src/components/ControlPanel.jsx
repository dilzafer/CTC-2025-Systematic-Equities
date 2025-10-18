/**
 * ControlPanel Component
 *
 * Main control panel for trading strategies.
 * Includes ultra-long, ultra-short, exit, and arbitrage controls.
 */

import { useState, useEffect } from 'react';
import StrategyButton from './StrategyButton';
import PositionDisplay from './PositionDisplay';
import StatusIndicator from './StatusIndicator';
import * as api from '../services/api';
import './ControlPanel.css';

const ControlPanel = () => {
  const [positions, setPositions] = useState({});
  const [botStatus, setBotStatus] = useState({
    running_strategies: [],
    arbitrage_running: false
  });
  const [connected, setConnected] = useState(false);

  // Fetch positions and status periodically
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [posData, statusData] = await Promise.all([
          api.getPositions(),
          api.getBotStatus()
        ]);

        if (posData.success) {
          setPositions(posData.positions);
        }

        if (statusData.success) {
          setBotStatus(statusData);
        }

        setConnected(true);
      } catch (error) {
        console.error('Error fetching data:', error);
        setConnected(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleArbitrageToggle = async () => {
    if (botStatus.arbitrage_running) {
      await api.stopArbitrage();
    } else {
      await api.startArbitrage();
    }
  };

  return (
    <div className="control-panel">
      <header className="panel-header">
        <h1>CTC Control Panel Sys Equities</h1>
        <p className="subtitle">Team from Harvard - Matthew, Dilzafer, Magnus, Param</p>
      </header>

      <StatusIndicator
        runningStrategies={botStatus.running_strategies}
        arbitrageRunning={botStatus.arbitrage_running}
        connected={connected}
      />

      <PositionDisplay positions={positions} />

      <div className="strategies-section">
        <div className="strategy-group">
          <h2>Ultra-Long Strategies</h2>
          <div className="button-grid">
            <StrategyButton
              label="Ultra-Long AAA"
              onClick={api.startUltraLongAAA}
              variant="long"
            />
            <StrategyButton
              label="Ultra-Long BBB"
              onClick={api.startUltraLongBBB}
              variant="long"
            />
            <StrategyButton
              label="Ultra-Long CCC"
              onClick={api.startUltraLongCCC}
              variant="long"
            />
          </div>

          <div className="button-grid">
            <StrategyButton
              label="Exit Long AAA"
              onClick={api.exitLongAAA}
              variant="exit"
            />
            <StrategyButton
              label="Exit Long BBB"
              onClick={api.exitLongBBB}
              variant="exit"
            />
            <StrategyButton
              label="Exit Long CCC"
              onClick={api.exitLongCCC}
              variant="exit"
            />
          </div>
        </div>

        <div className="strategy-group">
          <h2>Ultra-Short Strategies</h2>
          <div className="button-grid">
            <StrategyButton
              label="Ultra-Short AAA"
              onClick={api.startUltraShortAAA}
              variant="short"
            />
            <StrategyButton
              label="Ultra-Short BBB"
              onClick={api.startUltraShortBBB}
              variant="short"
            />
            <StrategyButton
              label="Ultra-Short CCC"
              onClick={api.startUltraShortCCC}
              variant="short"
            />
          </div>

          <div className="button-grid">
            <StrategyButton
              label="Exit Short AAA"
              onClick={api.exitShortAAA}
              variant="exit"
            />
            <StrategyButton
              label="Exit Short BBB"
              onClick={api.exitShortBBB}
              variant="exit"
            />
            <StrategyButton
              label="Exit Short CCC"
              onClick={api.exitShortCCC}
              variant="exit"
            />
          </div>
        </div>

        <div className="strategy-group">
          <h2>Arbitrage Control</h2>
          <div className="arbitrage-controls">
            <StrategyButton
              label={botStatus.arbitrage_running ? "Stop Arbitrage" : "Start Arbitrage"}
              onClick={handleArbitrageToggle}
              variant="arbitrage"
            />
            <p className="arbitrage-info">
              {botStatus.arbitrage_running
                ? "✓ Arbitrage is actively monitoring for opportunities"
                : "○ Arbitrage is stopped - click to enable"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
