#!/usr/bin/env python3
"""
Flask API Server for Trading Bot Control

This server provides REST API endpoints to control the trading bot
from a web frontend, enabling manual execution of strategies and
monitoring of positions.
"""

import os
import threading
from typing import Dict, Any, Optional
from flask import Flask, jsonify, request
from flask_cors import CORS

# Import bot functions
from bot import (
    get_positions,
    get_order_book,
    ultra_long_aaa, ultra_long_bbb, ultra_long_ccc,
    ultra_short_aaa, ultra_short_bbb, ultra_short_ccc,
    exit_ultra_long_aaa, exit_ultra_long_bbb, exit_ultra_long_ccc,
    exit_ultra_short_aaa, exit_ultra_short_bbb, exit_ultra_short_ccc,
    arbitrage_loop,
    DEFAULT_API_KEY
)

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Configuration - Hardcoded for deployment
API_URL = os.environ.get("CTC_API_URL", "https://cornelltradingcompetition.org")
API_KEY = os.environ.get("CTC_API_KEY", "xLw2g_6L6hqJ76LrmOfgJo_fKF6uNybtSx2HXHbXpiI")

# Global state for running strategies
strategy_threads: Dict[str, threading.Thread] = {}
stop_flags: Dict[str, threading.Event] = {}
arbitrage_running = False


# ----------------------------
# Helper Functions
# ----------------------------
def run_strategy_in_thread(strategy_name: str, strategy_func):
    """
    Run a strategy function in a background thread.
    """
    global strategy_threads, stop_flags

    if strategy_name in strategy_threads and strategy_threads[strategy_name].is_alive():
        return {"error": f"Strategy '{strategy_name}' is already running"}, 400

    # Create stop flag
    stop_flag = threading.Event()
    stop_flags[strategy_name] = stop_flag

    def wrapped_strategy():
        try:
            strategy_func(API_URL, API_KEY)
        except Exception as e:
            print(f"[API SERVER] Error in {strategy_name}: {e}")
        finally:
            # Cleanup
            if strategy_name in strategy_threads:
                del strategy_threads[strategy_name]
            if strategy_name in stop_flags:
                del stop_flags[strategy_name]

    # Start thread
    thread = threading.Thread(target=wrapped_strategy, daemon=True)
    strategy_threads[strategy_name] = thread
    thread.start()

    return {"message": f"Strategy '{strategy_name}' started successfully"}, 200


# ----------------------------
# API Endpoints
# ----------------------------

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "Trading bot API server is running"}), 200


@app.route('/api/positions', methods=['GET'])
def get_current_positions():
    """Get current positions for all symbols."""
    try:
        positions = get_positions(API_URL, API_KEY)
        return jsonify({
            "success": True,
            "positions": positions
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/orderbook/<symbol>', methods=['GET'])
def get_symbol_orderbook(symbol: str):
    """Get order book for a specific symbol."""
    try:
        order_book = get_order_book(API_URL, API_KEY, symbol.upper())
        return jsonify({
            "success": True,
            "symbol": symbol.upper(),
            "orderbook": order_book
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_bot_status():
    """Get status of all running strategies."""
    global strategy_threads, arbitrage_running

    running_strategies = [name for name, thread in strategy_threads.items() if thread.is_alive()]

    return jsonify({
        "success": True,
        "running_strategies": running_strategies,
        "arbitrage_running": arbitrage_running
    }), 200


# ----------------------------
# Ultra-Long Strategy Endpoints
# ----------------------------

@app.route('/api/strategy/ultra-long-aaa', methods=['POST'])
def start_ultra_long_aaa():
    """Start ultra-long AAA strategy."""
    return run_strategy_in_thread("ultra_long_aaa", ultra_long_aaa)


@app.route('/api/strategy/ultra-long-bbb', methods=['POST'])
def start_ultra_long_bbb():
    """Start ultra-long BBB strategy."""
    return run_strategy_in_thread("ultra_long_bbb", ultra_long_bbb)


@app.route('/api/strategy/ultra-long-ccc', methods=['POST'])
def start_ultra_long_ccc():
    """Start ultra-long CCC strategy."""
    return run_strategy_in_thread("ultra_long_ccc", ultra_long_ccc)


# ----------------------------
# Ultra-Short Strategy Endpoints
# ----------------------------

@app.route('/api/strategy/ultra-short-aaa', methods=['POST'])
def start_ultra_short_aaa():
    """Start ultra-short AAA strategy."""
    return run_strategy_in_thread("ultra_short_aaa", ultra_short_aaa)


@app.route('/api/strategy/ultra-short-bbb', methods=['POST'])
def start_ultra_short_bbb():
    """Start ultra-short BBB strategy."""
    return run_strategy_in_thread("ultra_short_bbb", ultra_short_bbb)


@app.route('/api/strategy/ultra-short-ccc', methods=['POST'])
def start_ultra_short_ccc():
    """Start ultra-short CCC strategy."""
    return run_strategy_in_thread("ultra_short_ccc", ultra_short_ccc)


# ----------------------------
# Exit Strategy Endpoints
# ----------------------------

@app.route('/api/strategy/exit-long-aaa', methods=['POST'])
def exit_long_aaa():
    """Exit ultra-long AAA position."""
    return run_strategy_in_thread("exit_ultra_long_aaa", exit_ultra_long_aaa)


@app.route('/api/strategy/exit-long-bbb', methods=['POST'])
def exit_long_bbb():
    """Exit ultra-long BBB position."""
    return run_strategy_in_thread("exit_ultra_long_bbb", exit_ultra_long_bbb)


@app.route('/api/strategy/exit-long-ccc', methods=['POST'])
def exit_long_ccc():
    """Exit ultra-long CCC position."""
    return run_strategy_in_thread("exit_ultra_long_ccc", exit_ultra_long_ccc)


@app.route('/api/strategy/exit-short-aaa', methods=['POST'])
def exit_short_aaa():
    """Exit ultra-short AAA position."""
    return run_strategy_in_thread("exit_ultra_short_aaa", exit_ultra_short_aaa)


@app.route('/api/strategy/exit-short-bbb', methods=['POST'])
def exit_short_bbb():
    """Exit ultra-short BBB position."""
    return run_strategy_in_thread("exit_ultra_short_bbb", exit_ultra_short_bbb)


@app.route('/api/strategy/exit-short-ccc', methods=['POST'])
def exit_short_ccc():
    """Exit ultra-short CCC position."""
    return run_strategy_in_thread("exit_ultra_short_ccc", exit_ultra_short_ccc)


# ----------------------------
# Arbitrage Control Endpoints
# ----------------------------

@app.route('/api/arbitrage/start', methods=['POST'])
def start_arbitrage():
    """Start HIGH-FREQUENCY arbitrage loop."""
    global arbitrage_running, strategy_threads

    if arbitrage_running:
        return jsonify({"error": "Arbitrage is already running"}), 400

    # Default to 1ms (0.001s) for high-frequency trading
    # Frontend can override with custom interval
    interval = request.json.get('interval', 0.001) if request.json else 0.001

    # Validate interval (prevent extreme values that could cause issues)
    if interval < 0:
        interval = 0  # 0 = maximum speed
    elif interval > 10:
        interval = 10  # Cap at 10 seconds

    def arbitrage_wrapper():
        global arbitrage_running
        arbitrage_running = True
        try:
            arbitrage_loop(API_URL, API_KEY, interval=interval)
        except Exception as e:
            print(f"[API SERVER] Arbitrage error: {e}")
        finally:
            arbitrage_running = False

    thread = threading.Thread(target=arbitrage_wrapper, daemon=True)
    strategy_threads["arbitrage"] = thread
    thread.start()

    return jsonify({
        "message": "High-frequency arbitrage started successfully",
        "interval_ms": interval * 1000,
        "estimated_checks_per_second": int(1 / interval) if interval > 0 else "unlimited"
    }), 200


@app.route('/api/arbitrage/stop', methods=['POST'])
def stop_arbitrage():
    """Stop arbitrage loop."""
    global arbitrage_running, strategy_threads

    if not arbitrage_running:
        return jsonify({"error": "Arbitrage is not running"}), 400

    # Set stop flag (arbitrage_loop needs to be modified to check this)
    arbitrage_running = False

    # Force stop the thread (note: this is not graceful)
    if "arbitrage" in strategy_threads:
        # The thread will stop on its own when the loop checks the flag
        del strategy_threads["arbitrage"]

    return jsonify({"message": "Arbitrage stop signal sent"}), 200


# ----------------------------
# Main
# ----------------------------

def main():
    """Start the Flask API server."""
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    print(f"[API SERVER] Starting Flask server on port {port}")
    print(f"[API SERVER] Trading API URL: {API_URL}")
    print(f"[API SERVER] Debug mode: {debug}")

    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
