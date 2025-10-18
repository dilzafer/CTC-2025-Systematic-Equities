# CTC-2025-Systematic-Equities

Comprehensive trading bot with web-based control panel for the Cornell Trading Competition 2025 - Systematic Equities case.

## 🚀 Features

### Trading Strategies
- **ETF Arbitrage**: Automated arbitrage between ETF and components with instant position netting
- **Ultra-Long Positions**: Build maximum long positions (+500) in AAA, BBB, or CCC
- **Ultra-Short Positions**: Build maximum short positions (-500) in AAA, BBB, or CCC
- **Smart Exit Functions**: Intelligently unwind all long/short positions using ETF creation/redemption

### Web Control Panel
- **Real-Time Position Monitoring**: Live position display updating every second
- **One-Click Strategy Execution**: Professional UI for manual strategy control
- **Arbitrage Toggle**: Manual start/stop control for arbitrage algorithm
- **Status Dashboard**: Track running strategies and connection status
- **Dark Trading Theme**: Professional interface optimized for trading environments

## 📋 Requirements

### Backend
- **Python 3.12+**
- **requests** - API communication
- **flask** - API server
- **flask-cors** - Cross-origin resource sharing

Install via:
```bash
pip install requests flask flask-cors
```

### Frontend
- **Node.js 18+**
- **npm** or **yarn**

## 🔑 API Key Setup

### Base URL
`https://cornelltradingcompetition.org`

### How to Get an API Key

1. Visit [https://cornelltradingcompetition.org/](https://cornelltradingcompetition.org/)
2. Sign in with **Google**
3. After onboarding (create or join a team), go to the **Team** page
4. As a **team owner**, navigate to the **API Keys** section
5. Create a new key for your bot and **copy the key** when prompted

**Note**: API key is pre-configured in `bot.py` as `DEFAULT_API_KEY`

## 🎯 Quick Start

### Option 1: Command-Line Usage

#### Run Arbitrage Only
```bash
python bot.py --arbitrage-only
```

#### Execute Ultra-Long Strategies
```bash
python bot.py --ultra-long-aaa
python bot.py --ultra-long-bbb
python bot.py --ultra-long-ccc
```

#### Execute Ultra-Short Strategies
```bash
python bot.py --ultra-short-aaa
python bot.py --ultra-short-bbb
python bot.py --ultra-short-ccc
```

#### Exit Positions
```bash
python bot.py --exit-ultra-long-aaa
python bot.py --exit-ultra-short-ccc
```

### Option 2: Web Control Panel (Recommended)

#### 1. Start the API Server
```bash
python api_server.py
```
Server runs on `http://localhost:5000`

#### 2. Start the React Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend available at `http://localhost:3000`

#### 3. Use the Web Interface
- Click strategy buttons to execute
- Monitor positions in real-time
- Toggle arbitrage on/off
- View active strategies

## 📚 Strategy Documentation

### ETF Arbitrage

**Spread 1: ETF Overpriced**
- Condition: ETF bid > sum(AAA ask + BBB ask + CCC ask)
- Action: Sell ETF, buy components
- Netting: Immediately create ETF from components → all positions = 0

**Spread 2: ETF Underpriced**
- Condition: ETF ask < sum(AAA bid + BBB bid + CCC bid)
- Action: Buy ETF, sell components
- Netting: Immediately redeem ETF into components → all positions = 0

### Ultra-Long Strategy (Example: AAA)

**Mechanism**:
1. Buy AAA directly up to position limit (+500)
2. Loop: Buy ETF + Sell BBB + Sell CCC → Redeem ETF
3. Net effect: +AAA (other positions cancel out)
4. Repeat until all position limits reached

**Position Limits**: All assets constrained to [-500, +500]

### Ultra-Short Strategy (Example: AAA)

**Mechanism**:
1. Sell AAA directly down to position limit (-500)
2. Loop: Sell ETF + Buy BBB + Buy CCC → Create ETF
3. Net effect: -AAA (other positions cancel out)
4. Repeat until all position limits reached

### Exit Strategies

**Exit Ultra-Long**:
1. Sell target component directly
2. Create ETF from remaining components
3. Repeat until all positions liquidated

**Exit Ultra-Short**:
1. Buy back short component directly
2. Use ETF creation/redemption to close remaining positions
3. Repeat until all positions neutralized

## 🏗️ Architecture

### Backend Components

**bot.py**: Core trading logic
- Strategy implementations (ultra-long, ultra-short, arbitrage)
- ETF creation/redemption functions
- Position limit enforcement
- Command-line interface

**api_server.py**: Flask REST API
- HTTP endpoints for all strategies
- Thread management for concurrent execution
- Real-time position retrieval
- Arbitrage control (start/stop)

### Frontend Components

**ControlPanel**: Main UI container
**StrategyButton**: Reusable strategy execution button
**PositionDisplay**: Real-time position visualization
**StatusIndicator**: Connection and strategy status
**API Client**: HTTP communication layer

## 🔧 Configuration

### Environment Variables

```bash
# Backend
export CTC_API_URL="https://cornelltradingcompetition.org"
export CTC_API_KEY="your_api_key_here"

# Frontend
VITE_API_URL=http://localhost:5000
```

### Custom Settings

Edit `bot.py`:
```python
DEFAULT_API_KEY = "your_key_here"
POSITION_LIMIT = 500  # Adjust if needed
```

## 📡 API Endpoints

### Strategy Execution
- `POST /api/strategy/ultra-long-aaa` - Start ultra-long AAA
- `POST /api/strategy/ultra-short-bbb` - Start ultra-short BBB
- `POST /api/strategy/exit-long-ccc` - Exit long CCC
- `POST /api/strategy/exit-short-aaa` - Exit short AAA

### Data Retrieval
- `GET /api/positions` - Get current positions
- `GET /api/orderbook/{symbol}` - Get order book
- `GET /api/status` - Get bot status

### Arbitrage Control
- `POST /api/arbitrage/start` - Start arbitrage
- `POST /api/arbitrage/stop` - Stop arbitrage

## 🎨 Color Coding (Frontend)

- **Green**: Ultra-long strategies
- **Red**: Ultra-short strategies
- **Orange**: Exit strategies
- **Purple/Blue**: Arbitrage control

## 🐛 Troubleshooting

**API Connection Issues**:
- Verify API key is correct
- Check CTC API URL is accessible
- Ensure firewall allows outbound connections

**Frontend Won't Start**:
- Run `npm install` in frontend directory
- Check Node.js version (18+)
- Verify API server is running

**Strategies Not Executing**:
- Check bot.py console for errors
- Verify position limits not exceeded
- Ensure market has sufficient liquidity

## 📄 Files Structure

```
CTC-2025-Systematic-Equities/
├── bot.py                  # Core trading bot
├── api_server.py          # Flask REST API
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── services/      # API client
│   │   ├── App.jsx        # Main app
│   │   └── main.jsx       # Entry point
│   ├── package.json
│   └── vite.config.js
└── README.md              # This file
```

## ⚠️ Safety Features

- **Position Limit Enforcement**: Hard limits at ±500 for all assets
- **Liquidity Matching**: 1-to-1 matching across all trade legs
- **Error Handling**: Comprehensive try-catch blocks
- **Graceful Degradation**: Strategies stop safely on errors
- **Real-Time Monitoring**: Live position tracking prevents overexposure

## 🏆 Competition Day Checklist

- [ ] Test all strategies on practice server
- [ ] Verify API key is active
- [ ] Check frontend builds successfully
- [ ] Test arbitrage on/off controls
- [ ] Confirm position limits working
- [ ] Review strategy execution logs
- [ ] Backup API key securely

## 📞 Support

For issues or questions:
- Check console logs for error messages
- Review API server status at `http://localhost:5000/api/health`
- Verify trading API status at Cornell TradingCompetition website

## 📜 License

MIT - Cornell Trading Competition 2025

---

**Built for CTC 2025 - Systematic Equities Case**
