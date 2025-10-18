# CTC Trading Bot - React Frontend

Professional trading control panel for the Cornell Trading Competition 2025 Systematic Equities case.

## Features

- **Ultra-Long Strategies**: Build maximum long positions (AAA, BBB, CCC)
- **Ultra-Short Strategies**: Build maximum short positions (AAA, BBB, CCC)
- **Exit Functions**: Cleanly exit all long/short positions
- **Arbitrage Control**: Manual start/stop for ETF arbitrage
- **Real-Time Monitoring**: Live position display with 1-second refresh
- **Status Dashboard**: Track running strategies and connection status
- **Professional UI**: Dark theme optimized for trading environments

## Setup Instructions

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+ with Flask and flask-cors installed
- Trading bot API server running (see api_server.py)

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Production Build

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Architecture

### Components

- **ControlPanel**: Main container managing all sections
- **StrategyButton**: Reusable button with loading/success/error states
- **PositionDisplay**: Visual position indicators with progress bars
- **StatusIndicator**: Connection and strategy status display

### API Client

The `api.js` service module provides:
- All strategy execution endpoints
- Position and order book retrieval
- Arbitrage control
- Error handling and user-friendly messages

## Usage

### Starting a Strategy

1. Click any strategy button (e.g., "Ultra-Long AAA")
2. Button shows "Running..." state
3. Success/error message appears below button
4. Strategy continues in background until complete

### Monitoring Positions

- Positions update every 1 second
- Green values: Long positions
- Red values: Short positions
- Progress bars show proximity to ±500 limits

### Arbitrage Control

- Click "Start Arbitrage" to enable continuous monitoring
- Click "Stop Arbitrage" to disable
- Status indicator shows current state

## Configuration

Create `.env` file for custom API URL:
```
VITE_API_URL=http://your-api-server:5000
```

Default: `http://localhost:5000`

## Color Coding

- **Green**: Ultra-long strategies
- **Red**: Ultra-short strategies
- **Orange**: Exit strategies
- **Purple/Blue**: Arbitrage control

## Troubleshooting

**Cannot connect to server**:
- Ensure Flask API server is running: `python api_server.py`
- Check API server URL in browser console
- Verify CORS is enabled on backend

**Strategies not starting**:
- Check browser console for errors
- Verify API key is set in `api_server.py`
- Ensure trading API is accessible

**Positions not updating**:
- Check network tab for failed requests
- Verify `/api/positions` endpoint is working
- Restart both frontend and backend

## Development

### File Structure
```
frontend/
├── public/          # Static assets
├── src/
│   ├── components/  # React components
│   ├── services/    # API client
│   ├── App.jsx      # Main app
│   └── main.jsx     # Entry point
├── package.json
└── vite.config.js
```

### Adding New Strategies

1. Add API function in `services/api.js`
2. Add button in `ControlPanel.jsx`
3. Choose appropriate variant color
4. Test with backend endpoint

## License

MIT - Cornell Trading Competition 2025
