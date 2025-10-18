/**
 * ControlPanel Component
 *
 * Main control panel for trading strategies.
 * Includes ultra-long, ultra-short, exit, and arbitrage controls.
 */

import { useState, useEffect, useRef } from 'react';
import StrategyButton from './StrategyButton';
import PositionDisplay from './PositionDisplay';
import StatusIndicator from './StatusIndicator';
import * as tradingApi from '../services/tradingApi';
import './ControlPanel.css';

const ControlPanel = () => {
  const [positions, setPositions] = useState({});
  const [arbitrageRunning, setArbitrageRunning] = useState(false);
  const [connected, setConnected] = useState(false);
  const [runningStrategies, setRunningStrategies] = useState([]);
  const arbitrageStopSignal = useRef({ stopped: false });

  // Fetch positions periodically
  useEffect(() => {
    const fetchPositions = async () => {
      try {
        const posData = await tradingApi.getPositions();
        setPositions(posData.positions || {});
        setConnected(true);
      } catch (error) {
        console.error('Error fetching positions:', error);
        setConnected(false);
      }
    };

    fetchPositions();
    const interval = setInterval(fetchPositions, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleArbitrageToggle = async () => {
    if (arbitrageRunning) {
      // Stop arbitrage
      arbitrageStopSignal.current.stopped = true;
      setArbitrageRunning(false);
    } else {
      // Start arbitrage
      arbitrageStopSignal.current = { stopped: false };
      setArbitrageRunning(true);

      tradingApi.runArbitrage(
        (message) => console.log('[ARBITRAGE]', message),
        arbitrageStopSignal.current
      );
    }
  };

  return (
    <div className="control-panel">
      <header className="panel-header">
        <h1>CTC Control Panel Sys Equities</h1>
        <p className="subtitle">Team from Harvard - Matthew, Dilzafer, Magnus, Param</p>
      </header>

      <StatusIndicator
        runningStrategies={runningStrategies}
        arbitrageRunning={arbitrageRunning}
        connected={connected}
      />

      <PositionDisplay positions={positions} />

      <div className="strategies-section">
        <div className="strategy-group">
          <h2>Ultra-Long Strategies</h2>
          <div className="button-grid">
            <StrategyButton
              label="Ultra-Long AAA"
              onClick={tradingApi.ultraLongAAA}
              variant="long"
            />
            <StrategyButton
              label="Ultra-Long BBB"
              onClick={tradingApi.ultraLongBBB}
              variant="long"
            />
            <StrategyButton
              label="Ultra-Long CCC"
              onClick={tradingApi.ultraLongCCC}
              variant="long"
            />
          </div>
        </div>

        <div className="strategy-group">
          <h2>Ultra-Short Strategies</h2>
          <div className="button-grid">
            <StrategyButton
              label="Ultra-Short AAA"
              onClick={tradingApi.ultraShortAAA}
              variant="short"
            />
            <StrategyButton
              label="Ultra-Short BBB"
              onClick={tradingApi.ultraShortBBB}
              variant="short"
            />
            <StrategyButton
              label="Ultra-Short CCC"
              onClick={tradingApi.ultraShortCCC}
              variant="short"
            />
          </div>
        </div>

        <div className="strategy-group">
          <h2>Arbitrage Control</h2>
          <div className="arbitrage-controls">
            <StrategyButton
              label={arbitrageRunning ? "Stop Arbitrage" : "Start Arbitrage"}
              onClick={handleArbitrageToggle}
              variant="arbitrage"
            />
            <p className="arbitrage-info">
              {arbitrageRunning
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
