/**
 * PositionDisplay Component
 *
 * Displays current positions for all symbols with visual indicators.
 * Features: Color-coded values, progress bars showing position limits.
 */

import './PositionDisplay.css';

const POSITION_LIMIT = 500;

const PositionDisplay = ({ positions }) => {
  const symbols = ['AAA', 'BBB', 'CCC', 'ETF'];

  const getPositionColor = (position) => {
    if (position > 0) return 'positive';
    if (position < 0) return 'negative';
    return 'zero';
  };

  const getPositionPercentage = (position) => {
    // Calculate percentage for progress bar (-500 to +500 maps to 0% to 100%)
    return ((position + POSITION_LIMIT) / (2 * POSITION_LIMIT)) * 100;
  };

  return (
    <div className="position-display">
      <h3>Current Positions</h3>
      <div className="positions-grid">
        {symbols.map((symbol) => {
          const position = positions[symbol] || 0;
          const percentage = getPositionPercentage(position);
          const colorClass = getPositionColor(position);

          return (
            <div key={symbol} className="position-card">
              <div className="position-header">
                <span className="symbol-name">{symbol}</span>
                <span className={`position-value ${colorClass}`}>
                  {position > 0 && '+'}{position}
                </span>
              </div>

              <div className="position-bar-container">
                <div className="position-bar">
                  <div
                    className={`position-fill ${colorClass}`}
                    style={{ width: `${percentage}%` }}
                  />
                  <div className="position-marker" style={{ left: '50%' }} />
                </div>
                <div className="position-labels">
                  <span>-{POSITION_LIMIT}</span>
                  <span>0</span>
                  <span>+{POSITION_LIMIT}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PositionDisplay;
