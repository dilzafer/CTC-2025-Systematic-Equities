#!/bin/bash

# Start server script for CTC Trading Bot
# This script starts both the Flask API server and React frontend

echo "🚀 Starting CTC Trading Bot Control Panel..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.12+"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Start Flask API server in background
echo "🔧 Starting Flask API server on port 5000..."
python3 api_server.py &
API_PID=$!
echo "   API Server PID: $API_PID"

# Wait for API server to start
sleep 2

# Install frontend dependencies if not already installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Start React frontend
echo "🎨 Starting React frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers started successfully!"
echo ""
echo "📊 Control Panel: http://localhost:3000"
echo "🔌 API Server: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user to press Ctrl+C
trap "echo ''; echo '🛑 Shutting down...'; kill $API_PID $FRONTEND_PID; exit" INT
wait
