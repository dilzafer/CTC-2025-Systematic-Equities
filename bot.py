#!/usr/bin/env python3
import os
import time
import json
import argparse
import random
import threading
from typing import Any, Optional
import requests


# ----------------------------
# Configuration
# ----------------------------
DEFAULT_API_KEY = "wxJM6xGFnLPodG5jLQUejTxRnL4SZog_3GS2_3h244Q"


# ----------------------------
# Helpers
# ----------------------------
def build_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key, "Content-Type": "application/json"}

def _raise_for_api_error(resp: requests.Response) -> None:
    if 200 <= resp.status_code < 300:
        return
    try:
        data = resp.json()
        detail = data.get("detail") if isinstance(data, dict) else None
    except Exception:
        detail = None
    msg = f"HTTP {resp.status_code}"
    if detail:
        msg += f": {detail}"
    raise RuntimeError(msg)


def api_get(base_url: str, path: str, api_key: str, params: Optional[dict[str, Any]] = None) -> Any:
    url = f"{base_url}{path}"
    resp = requests.get(url, headers=build_headers(api_key), params=params, timeout=15)
    _raise_for_api_error(resp)
    return resp.json()


def api_post(base_url: str, path: str, api_key: str, body: dict[str, Any]) -> Any:
    url = f"{base_url}{path}"
    resp = requests.post(url, headers=build_headers(api_key), data=json.dumps(body), timeout=10)
    if not (200 <= resp.status_code < 300):
        try:
            err = resp.json().get("detail", "")
        except Exception:
            err = resp.text
        raise RuntimeError(f"HTTP {resp.status_code}: {err}")
    return resp.json()


def place_order(api_url: str, api_key: str, order: dict[str, Any]) -> None:
    """Send a single order to the API."""
    try:
        res = api_post(api_url, "/api/v1/orders", api_key, order)
        print(
            f"[OK] {order['side'].upper():4} {order['symbol']:5} "
            f"{order['quantity']:>3} @ {order.get('price', 'MKT')} ({order['order_type']})"
        )
    except Exception as e:
        print(f"[ERR] Failed order for {order['symbol']}: {e}")

def list_symbols(base_url: str, api_key: str) -> None:
    data = api_get(base_url, "/api/v1/symbols", api_key)
    symbols = data.get("symbols", [])
    if not symbols:
        print("No symbols available.")
        return
    print("Available symbols:")
    for row in symbols:
        print(f"  - {row.get('symbol')}\t{row.get('name')}")

def list_open_orders(base_url: str, api_key: str, symbol: Optional[str] = None) -> None:
    params: dict[str, Any] = {}
    if symbol:
        params["symbol"] = symbol
    data = api_get(base_url, "/api/v1/orders/open", api_key, params=params)
    orders = data.get("orders", [])
    if not orders:
        print("No open orders.")
        return
    print("Open orders:")
    for o in orders:
        price_str = f" @ {o['price']}" if o.get("price") is not None else ""
        print(
            f"  - {o['order_id']} | {o['symbol']} {o['side']} {o['quantity']} {o['order_type']}{price_str} | {o['status']}"
        )


def get_order_book(base_url: str, api_key: str, symbol: str) -> dict[str, Any]:
    """Fetch the order book for a given symbol."""
    try:
        data = api_get(base_url, f"/api/v1/orderbook/{symbol}", api_key)
        return data
    except Exception as e:
        print(f"[ERR] Failed to get order book for {symbol}: {e}")
        return {}


def get_positions(base_url: str, api_key: str) -> dict[str, int]:
    """Fetch current positions for all symbols."""
    try:
        data = api_get(base_url, "/api/v1/positions", api_key)
        positions = {}
        for pos in data.get("positions", []):
            positions[pos["symbol"]] = pos.get("quantity", 0)
        return positions
    except Exception as e:
        print(f"[ERR] Failed to get positions: {e}")
        return {}


def create_etf(api_url: str, api_key: str, quantity: int) -> bool:
    """
    Create ETF shares by converting components (AAA+BBB+CCC) into ETF.

    Args:
        api_url: Base API URL
        api_key: API key
        quantity: Number of ETF shares to create

    Returns:
        True if successful, False otherwise
    """
    try:
        body = {"quantity": quantity}
        result = api_post(api_url, "/api/v1/etf/ETF/create", api_key, body)
        print(f"[ETF CREATE] Created {quantity} ETF units from components")
        return True
    except Exception as e:
        print(f"[ETF CREATE ERR] Failed to create {quantity} ETF: {e}")
        return False


def redeem_etf(api_url: str, api_key: str, quantity: int) -> bool:
    """
    Redeem ETF shares to get components (AAA+BBB+CCC).

    Args:
        api_url: Base API URL
        api_key: API key
        quantity: Number of ETF shares to redeem

    Returns:
        True if successful, False otherwise
    """
    try:
        body = {"quantity": quantity}
        result = api_post(api_url, "/api/v1/etf/ETF/redeem", api_key, body)
        print(f"[ETF REDEEM] Redeemed {quantity} ETF units into components")
        return True
    except Exception as e:
        print(f"[ETF REDEEM ERR] Failed to redeem {quantity} ETF: {e}")
        return False


# ----------------------------
# ETF Arbitrage Logic
# ----------------------------
def get_best_bid_ask(order_book: dict[str, Any]) -> tuple[Optional[float], Optional[int], Optional[float], Optional[int]]:
    """
    Extract best bid price/qty and best ask price/qty from order book.
    Returns: (bid_price, bid_qty, ask_price, ask_qty)
    """
    bids = order_book.get("bids", [])
    asks = order_book.get("asks", [])

    best_bid_price = bids[0]["price"] if bids else None
    best_bid_qty = bids[0]["quantity"] if bids else None
    best_ask_price = asks[0]["price"] if asks else None
    best_ask_qty = asks[0]["quantity"] if asks else None

    return best_bid_price, best_bid_qty, best_ask_price, best_ask_qty


def calculate_arbitrage_opportunities(
    etf_book: dict[str, Any],
    aaa_book: dict[str, Any],
    bbb_book: dict[str, Any],
    ccc_book: dict[str, Any]
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """
    Calculate both arbitrage opportunities:
    - Spread 1: ETF bid > sum(component asks) → sell ETF, buy components
    - Spread 2: ETF ask < sum(component bids) → buy ETF, sell components

    Returns: (spread1_opportunity, spread2_opportunity)
    Each opportunity dict contains: {spread, max_quantity, etf_price, component_prices}
    """
    etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
    aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)
    bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)
    ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

    spread1_opp = None
    spread2_opp = None

    # Spread 1: Sell ETF (at bid), Buy components (at ask)
    # ETF is overpriced if its bid > sum of component asks
    if all(x is not None for x in [etf_bid, etf_bid_qty, aaa_ask, aaa_ask_qty, bbb_ask, bbb_ask_qty, ccc_ask, ccc_ask_qty]):
        component_ask_sum = aaa_ask + bbb_ask + ccc_ask
        spread1 = etf_bid - component_ask_sum

        if spread1 > 0:  # Profitable
            # Liquidity constraint: min of ETF bid qty and all component ask qtys
            max_qty = min(etf_bid_qty, aaa_ask_qty, bbb_ask_qty, ccc_ask_qty)
            spread1_opp = {
                "spread": spread1,
                "max_quantity": max_qty,
                "etf_price": etf_bid,
                "aaa_price": aaa_ask,
                "bbb_price": bbb_ask,
                "ccc_price": ccc_ask
            }

    # Spread 2: Buy ETF (at ask), Sell components (at bid)
    # ETF is underpriced if its ask < sum of component bids
    if all(x is not None for x in [etf_ask, etf_ask_qty, aaa_bid, aaa_bid_qty, bbb_bid, bbb_bid_qty, ccc_bid, ccc_bid_qty]):
        component_bid_sum = aaa_bid + bbb_bid + ccc_bid
        spread2 = component_bid_sum - etf_ask

        if spread2 > 0:  # Profitable
            # Liquidity constraint: min of ETF ask qty and all component bid qtys
            max_qty = min(etf_ask_qty, aaa_bid_qty, bbb_bid_qty, ccc_bid_qty)
            spread2_opp = {
                "spread": spread2,
                "max_quantity": max_qty,
                "etf_price": etf_ask,
                "aaa_price": aaa_bid,
                "bbb_price": bbb_bid,
                "ccc_price": ccc_bid
            }

    return spread1_opp, spread2_opp


def check_position_limits(
    positions: dict[str, int],
    trade_qty: int,
    trade_type: str
) -> int:
    """
    Check position limits and return maximum allowable trade quantity.

    Args:
        positions: Current positions for all symbols (ETF, AAA, BBB, CCC)
        trade_qty: Desired trade quantity
        trade_type: Either "spread1" (sell ETF, buy components) or "spread2" (buy ETF, sell components)

    Returns:
        Maximum allowed trade quantity respecting [-500, +500] limits for all 4 assets
    """
    POSITION_LIMIT = 500

    # Get current positions, default to 0 if not found
    etf_pos = positions.get("ETF", 0)
    aaa_pos = positions.get("AAA", 0)
    bbb_pos = positions.get("BBB", 0)
    ccc_pos = positions.get("CCC", 0)

    max_qty = trade_qty

    if trade_type == "spread1":
        # Spread 1: Sell ETF (decrease ETF position), Buy components (increase component positions)
        # ETF: position will decrease by trade_qty
        max_etf_sell = etf_pos - (-POSITION_LIMIT)  # How much we can sell before hitting -500
        # Components: positions will increase by trade_qty
        max_aaa_buy = POSITION_LIMIT - aaa_pos  # How much we can buy before hitting +500
        max_bbb_buy = POSITION_LIMIT - bbb_pos
        max_ccc_buy = POSITION_LIMIT - ccc_pos

        max_qty = min(max_qty, max_etf_sell, max_aaa_buy, max_bbb_buy, max_ccc_buy)

    elif trade_type == "spread2":
        # Spread 2: Buy ETF (increase ETF position), Sell components (decrease component positions)
        # ETF: position will increase by trade_qty
        max_etf_buy = POSITION_LIMIT - etf_pos  # How much we can buy before hitting +500
        # Components: positions will decrease by trade_qty
        max_aaa_sell = aaa_pos - (-POSITION_LIMIT)  # How much we can sell before hitting -500
        max_bbb_sell = bbb_pos - (-POSITION_LIMIT)
        max_ccc_sell = ccc_pos - (-POSITION_LIMIT)

        max_qty = min(max_qty, max_etf_buy, max_aaa_sell, max_bbb_sell, max_ccc_sell)

    return max(0, max_qty)  # Ensure non-negative


def execute_arbitrage_trade(
    api_url: str,
    api_key: str,
    opportunity: dict[str, Any],
    trade_type: str,
    trade_qty: int
) -> bool:
    """
    Execute a 4-leg arbitrage trade atomically, then immediately net out positions.

    Args:
        api_url: Base API URL
        api_key: API key
        opportunity: Opportunity dict with prices
        trade_type: "spread1" or "spread2"
        trade_qty: Quantity to trade

    Returns:
        True if all orders placed successfully, False otherwise
    """
    if trade_qty <= 0:
        return False

    orders = []

    if trade_type == "spread1":
        # Spread 1: Sell ETF, Buy components
        orders = [
            {"symbol": "ETF", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": opportunity["etf_price"]},
            {"symbol": "AAA", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": opportunity["aaa_price"]},
            {"symbol": "BBB", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": opportunity["bbb_price"]},
            {"symbol": "CCC", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": opportunity["ccc_price"]},
        ]
    elif trade_type == "spread2":
        # Spread 2: Buy ETF, Sell components
        orders = [
            {"symbol": "ETF", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": opportunity["etf_price"]},
            {"symbol": "AAA", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": opportunity["aaa_price"]},
            {"symbol": "BBB", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": opportunity["bbb_price"]},
            {"symbol": "CCC", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": opportunity["ccc_price"]},
        ]

    # Execute all orders
    success = True
    for order in orders:
        try:
            api_post(api_url, "/api/v1/orders", api_key, order)
        except Exception as e:
            print(f"[ARB ERR] Failed to place {order['side']} {order['symbol']}: {e}")
            success = False

    if success:
        profit = opportunity["spread"] * trade_qty
        print(f"[ARB] {trade_type.upper()} executed: {trade_qty} units, spread={opportunity['spread']:.4f}, profit={profit:.2f}")

        # INSTANT POSITION NETTING
        # Wait briefly for orders to fill
        time.sleep(0.2)

        if trade_type == "spread1":
            # Spread 1: We now have long AAA+BBB+CCC, short ETF
            # Create ETF from components to net out all positions to 0
            create_etf(api_url, api_key, trade_qty)
            print(f"[ARB] Spread 1 netted: Created {trade_qty} ETF from components → all positions = 0")

        elif trade_type == "spread2":
            # Spread 2: We now have long ETF, short AAA+BBB+CCC
            # Redeem ETF to get components and net out all positions to 0
            redeem_etf(api_url, api_key, trade_qty)
            print(f"[ARB] Spread 2 netted: Redeemed {trade_qty} ETF into components → all positions = 0")

    return success


def run_arbitrage_strategy(api_url: str, api_key: str) -> None:
    """
    Main arbitrage strategy execution - checks for opportunities and executes trades.
    """
    try:
        # Fetch order books for all 4 securities
        etf_book = get_order_book(api_url, api_key, "ETF")
        aaa_book = get_order_book(api_url, api_key, "AAA")
        bbb_book = get_order_book(api_url, api_key, "BBB")
        ccc_book = get_order_book(api_url, api_key, "CCC")

        # Check if all order books are available
        if not all([etf_book, aaa_book, bbb_book, ccc_book]):
            return

        # Calculate arbitrage opportunities
        spread1_opp, spread2_opp = calculate_arbitrage_opportunities(
            etf_book, aaa_book, bbb_book, ccc_book
        )

        # Get current positions
        positions = get_positions(api_url, api_key)

        # Execute Spread 1 if available
        if spread1_opp:
            max_qty = check_position_limits(positions, spread1_opp["max_quantity"], "spread1")
            if max_qty > 0:
                execute_arbitrage_trade(api_url, api_key, spread1_opp, "spread1", max_qty)

        # Execute Spread 2 if available
        if spread2_opp:
            max_qty = check_position_limits(positions, spread2_opp["max_quantity"], "spread2")
            if max_qty > 0:
                execute_arbitrage_trade(api_url, api_key, spread2_opp, "spread2", max_qty)

    except Exception as e:
        print(f"[ARB ERR] Arbitrage strategy error: {e}")


def arbitrage_loop(api_url: str, api_key: str, interval: float = 0.1) -> None:
    """
    Continuous arbitrage monitoring loop that runs in a separate thread.

    Args:
        api_url: Base API URL
        api_key: API key
        interval: Sleep interval between checks (in seconds)
    """
    print("[ARB] Starting arbitrage monitoring loop...")
    while True:
        try:
            run_arbitrage_strategy(api_url, api_key)
            time.sleep(interval)
        except KeyboardInterrupt:
            print("[ARB] Arbitrage loop stopped by user.")
            break
        except Exception as e:
            print(f"[ARB ERR] Loop error: {e}")
            time.sleep(interval)


# ----------------------------
# Ultra-Long Strategies
# ----------------------------
def ultra_long_aaa(api_url: str, api_key: str) -> None:
    """
    Build maximum long position in AAA using ETF arbitrage mechanism.

    Strategy:
    1. Buy as much AAA directly (up to position limit 500)
    2. Loop: Buy ETF + Sell BBB + Sell CCC, then redeem ETF → net effect: +AAA
    3. Repeat until all position limits reached
    """
    POSITION_LIMIT = 500
    print("[ULTRA-LONG AAA] Starting ultra-long AAA strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[ULTRA-LONG AAA] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # Check if AAA is at limit
        if aaa_pos >= POSITION_LIMIT:
            print(f"[ULTRA-LONG AAA] AAA position limit reached ({aaa_pos}). Strategy complete.")
            break

        # Step 1: Buy AAA directly
        aaa_room = POSITION_LIMIT - aaa_pos
        if aaa_room > 0:
            aaa_book = get_order_book(api_url, api_key, "AAA")
            aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)

            if aaa_ask and aaa_ask_qty:
                buy_qty = min(aaa_room, aaa_ask_qty)
                order = {"symbol": "AAA", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": aaa_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[ULTRA-LONG AAA] Bought {buy_qty} AAA @ {aaa_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[ULTRA-LONG AAA ERR] Failed to buy AAA: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: Use ETF mechanism to gain more AAA
        # Calculate how much room we have in each position
        etf_room = POSITION_LIMIT - etf_pos  # Room to buy ETF
        bbb_sell_room = bbb_pos - (-POSITION_LIMIT)  # Room to sell BBB
        ccc_sell_room = ccc_pos - (-POSITION_LIMIT)  # Room to sell CCC
        aaa_room = POSITION_LIMIT - aaa_pos

        if etf_room <= 0 or bbb_sell_room <= 0 or ccc_sell_room <= 0 or aaa_room <= 0:
            print(f"[ULTRA-LONG AAA] Position limits reached. ETF room={etf_room}, BBB sell room={bbb_sell_room}, CCC sell room={ccc_sell_room}, AAA room={aaa_room}")
            break

        # Get order books
        etf_book = get_order_book(api_url, api_key, "ETF")
        bbb_book = get_order_book(api_url, api_key, "BBB")
        ccc_book = get_order_book(api_url, api_key, "CCC")

        etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
        bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)
        ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

        # Check if we have valid market data
        if not all([etf_ask, etf_ask_qty, bbb_bid, bbb_bid_qty, ccc_bid, ccc_bid_qty]):
            print("[ULTRA-LONG AAA] Insufficient market liquidity, waiting...")
            time.sleep(1)
            continue

        # Calculate trade quantity: min of all constraints
        trade_qty = min(etf_ask_qty, bbb_bid_qty, ccc_bid_qty, etf_room, bbb_sell_room, ccc_sell_room, aaa_room)

        if trade_qty <= 0:
            print("[ULTRA-LONG AAA] No tradeable quantity available")
            break

        print(f"[ULTRA-LONG AAA] Executing ETF mechanism: trade_qty={trade_qty}")

        # Execute: Buy ETF, Sell BBB, Sell CCC
        orders = [
            {"symbol": "ETF", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": etf_ask},
            {"symbol": "BBB", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": bbb_bid},
            {"symbol": "CCC", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": ccc_bid},
        ]

        success = True
        for order in orders:
            try:
                api_post(api_url, "/api/v1/orders", api_key, order)
                print(f"[ULTRA-LONG AAA] {order['side'].upper()} {order['quantity']} {order['symbol']} @ {order['price']}")
            except Exception as e:
                print(f"[ULTRA-LONG AAA ERR] Failed {order['side']} {order['symbol']}: {e}")
                success = False

        if success:
            # Wait for fills
            time.sleep(0.2)
            # Redeem ETF to get AAA+BBB+CCC
            redeem_etf(api_url, api_key, trade_qty)
            print(f"[ULTRA-LONG AAA] Net effect: +{trade_qty} AAA (BBB/CCC/ETF positions cancelled out)")

        time.sleep(0.5)

    print("[ULTRA-LONG AAA] Strategy complete!")


def ultra_long_bbb(api_url: str, api_key: str) -> None:
    """
    Build maximum long position in BBB using ETF arbitrage mechanism.

    Strategy:
    1. Buy as much BBB directly (up to position limit 500)
    2. Loop: Buy ETF + Sell AAA + Sell CCC, then redeem ETF → net effect: +BBB
    3. Repeat until all position limits reached
    """
    POSITION_LIMIT = 500
    print("[ULTRA-LONG BBB] Starting ultra-long BBB strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[ULTRA-LONG BBB] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # Check if BBB is at limit
        if bbb_pos >= POSITION_LIMIT:
            print(f"[ULTRA-LONG BBB] BBB position limit reached ({bbb_pos}). Strategy complete.")
            break

        # Step 1: Buy BBB directly
        bbb_room = POSITION_LIMIT - bbb_pos
        if bbb_room > 0:
            bbb_book = get_order_book(api_url, api_key, "BBB")
            bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)

            if bbb_ask and bbb_ask_qty:
                buy_qty = min(bbb_room, bbb_ask_qty)
                order = {"symbol": "BBB", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": bbb_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[ULTRA-LONG BBB] Bought {buy_qty} BBB @ {bbb_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[ULTRA-LONG BBB ERR] Failed to buy BBB: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: Use ETF mechanism to gain more BBB
        etf_room = POSITION_LIMIT - etf_pos
        aaa_sell_room = aaa_pos - (-POSITION_LIMIT)
        ccc_sell_room = ccc_pos - (-POSITION_LIMIT)
        bbb_room = POSITION_LIMIT - bbb_pos

        if etf_room <= 0 or aaa_sell_room <= 0 or ccc_sell_room <= 0 or bbb_room <= 0:
            print(f"[ULTRA-LONG BBB] Position limits reached. ETF room={etf_room}, AAA sell room={aaa_sell_room}, CCC sell room={ccc_sell_room}, BBB room={bbb_room}")
            break

        # Get order books
        etf_book = get_order_book(api_url, api_key, "ETF")
        aaa_book = get_order_book(api_url, api_key, "AAA")
        ccc_book = get_order_book(api_url, api_key, "CCC")

        etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
        aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)
        ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

        if not all([etf_ask, etf_ask_qty, aaa_bid, aaa_bid_qty, ccc_bid, ccc_bid_qty]):
            print("[ULTRA-LONG BBB] Insufficient market liquidity, waiting...")
            time.sleep(1)
            continue

        trade_qty = min(etf_ask_qty, aaa_bid_qty, ccc_bid_qty, etf_room, aaa_sell_room, ccc_sell_room, bbb_room)

        if trade_qty <= 0:
            print("[ULTRA-LONG BBB] No tradeable quantity available")
            break

        print(f"[ULTRA-LONG BBB] Executing ETF mechanism: trade_qty={trade_qty}")

        # Execute: Buy ETF, Sell AAA, Sell CCC
        orders = [
            {"symbol": "ETF", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": etf_ask},
            {"symbol": "AAA", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": aaa_bid},
            {"symbol": "CCC", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": ccc_bid},
        ]

        success = True
        for order in orders:
            try:
                api_post(api_url, "/api/v1/orders", api_key, order)
                print(f"[ULTRA-LONG BBB] {order['side'].upper()} {order['quantity']} {order['symbol']} @ {order['price']}")
            except Exception as e:
                print(f"[ULTRA-LONG BBB ERR] Failed {order['side']} {order['symbol']}: {e}")
                success = False

        if success:
            time.sleep(0.2)
            redeem_etf(api_url, api_key, trade_qty)
            print(f"[ULTRA-LONG BBB] Net effect: +{trade_qty} BBB (AAA/CCC/ETF positions cancelled out)")

        time.sleep(0.5)

    print("[ULTRA-LONG BBB] Strategy complete!")


def ultra_long_ccc(api_url: str, api_key: str) -> None:
    """
    Build maximum long position in CCC using ETF arbitrage mechanism.

    Strategy:
    1. Buy as much CCC directly (up to position limit 500)
    2. Loop: Buy ETF + Sell AAA + Sell BBB, then redeem ETF → net effect: +CCC
    3. Repeat until all position limits reached
    """
    POSITION_LIMIT = 500
    print("[ULTRA-LONG CCC] Starting ultra-long CCC strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[ULTRA-LONG CCC] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # Check if CCC is at limit
        if ccc_pos >= POSITION_LIMIT:
            print(f"[ULTRA-LONG CCC] CCC position limit reached ({ccc_pos}). Strategy complete.")
            break

        # Step 1: Buy CCC directly
        ccc_room = POSITION_LIMIT - ccc_pos
        if ccc_room > 0:
            ccc_book = get_order_book(api_url, api_key, "CCC")
            ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

            if ccc_ask and ccc_ask_qty:
                buy_qty = min(ccc_room, ccc_ask_qty)
                order = {"symbol": "CCC", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": ccc_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[ULTRA-LONG CCC] Bought {buy_qty} CCC @ {ccc_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[ULTRA-LONG CCC ERR] Failed to buy CCC: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: Use ETF mechanism to gain more CCC
        etf_room = POSITION_LIMIT - etf_pos
        aaa_sell_room = aaa_pos - (-POSITION_LIMIT)
        bbb_sell_room = bbb_pos - (-POSITION_LIMIT)
        ccc_room = POSITION_LIMIT - ccc_pos

        if etf_room <= 0 or aaa_sell_room <= 0 or bbb_sell_room <= 0 or ccc_room <= 0:
            print(f"[ULTRA-LONG CCC] Position limits reached. ETF room={etf_room}, AAA sell room={aaa_sell_room}, BBB sell room={bbb_sell_room}, CCC room={ccc_room}")
            break

        # Get order books
        etf_book = get_order_book(api_url, api_key, "ETF")
        aaa_book = get_order_book(api_url, api_key, "AAA")
        bbb_book = get_order_book(api_url, api_key, "BBB")

        etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
        aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)
        bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)

        if not all([etf_ask, etf_ask_qty, aaa_bid, aaa_bid_qty, bbb_bid, bbb_bid_qty]):
            print("[ULTRA-LONG CCC] Insufficient market liquidity, waiting...")
            time.sleep(1)
            continue

        trade_qty = min(etf_ask_qty, aaa_bid_qty, bbb_bid_qty, etf_room, aaa_sell_room, bbb_sell_room, ccc_room)

        if trade_qty <= 0:
            print("[ULTRA-LONG CCC] No tradeable quantity available")
            break

        print(f"[ULTRA-LONG CCC] Executing ETF mechanism: trade_qty={trade_qty}")

        # Execute: Buy ETF, Sell AAA, Sell BBB
        orders = [
            {"symbol": "ETF", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": etf_ask},
            {"symbol": "AAA", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": aaa_bid},
            {"symbol": "BBB", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": bbb_bid},
        ]

        success = True
        for order in orders:
            try:
                api_post(api_url, "/api/v1/orders", api_key, order)
                print(f"[ULTRA-LONG CCC] {order['side'].upper()} {order['quantity']} {order['symbol']} @ {order['price']}")
            except Exception as e:
                print(f"[ULTRA-LONG CCC ERR] Failed {order['side']} {order['symbol']}: {e}")
                success = False

        if success:
            time.sleep(0.2)
            redeem_etf(api_url, api_key, trade_qty)
            print(f"[ULTRA-LONG CCC] Net effect: +{trade_qty} CCC (AAA/BBB/ETF positions cancelled out)")

        time.sleep(0.5)

    print("[ULTRA-LONG CCC] Strategy complete!")


# ----------------------------
# Ultra-Short Strategies
# ----------------------------
def ultra_short_aaa(api_url: str, api_key: str) -> None:
    """
    Build maximum short position in AAA using ETF arbitrage mechanism.

    Strategy:
    1. Sell as much AAA directly (down to position limit -500)
    2. Loop: Sell ETF + Buy BBB + Buy CCC, then create ETF → net effect: -AAA
    3. Repeat until all position limits reached
    """
    POSITION_LIMIT = 500
    print("[ULTRA-SHORT AAA] Starting ultra-short AAA strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[ULTRA-SHORT AAA] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # Check if AAA is at negative limit
        if aaa_pos <= -POSITION_LIMIT:
            print(f"[ULTRA-SHORT AAA] AAA position limit reached ({aaa_pos}). Strategy complete.")
            break

        # Step 1: Sell AAA directly
        aaa_sell_room = aaa_pos - (-POSITION_LIMIT)  # How much we can sell before hitting -500
        if aaa_sell_room > 0:
            aaa_book = get_order_book(api_url, api_key, "AAA")
            aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)

            if aaa_bid and aaa_bid_qty:
                sell_qty = min(aaa_sell_room, aaa_bid_qty)
                order = {"symbol": "AAA", "side": "sell", "order_type": "limit", "quantity": sell_qty, "price": aaa_bid}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[ULTRA-SHORT AAA] Sold {sell_qty} AAA @ {aaa_bid}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[ULTRA-SHORT AAA ERR] Failed to sell AAA: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: Use ETF mechanism to gain more short AAA
        # We need to: Sell ETF, Buy BBB, Buy CCC, then Create ETF from BBB+CCC
        # Net effect: -AAA (because we're short ETF which contains AAA)

        # Calculate how much room we have in each position
        etf_sell_room = etf_pos - (-POSITION_LIMIT)  # Room to sell ETF
        bbb_buy_room = POSITION_LIMIT - bbb_pos  # Room to buy BBB
        ccc_buy_room = POSITION_LIMIT - ccc_pos  # Room to buy CCC
        aaa_short_room = aaa_pos - (-POSITION_LIMIT)  # Room to short more AAA

        if etf_sell_room <= 0 or bbb_buy_room <= 0 or ccc_buy_room <= 0 or aaa_short_room <= 0:
            print(f"[ULTRA-SHORT AAA] Position limits reached. ETF sell room={etf_sell_room}, BBB buy room={bbb_buy_room}, CCC buy room={ccc_buy_room}, AAA short room={aaa_short_room}")
            break

        # Get order books
        etf_book = get_order_book(api_url, api_key, "ETF")
        bbb_book = get_order_book(api_url, api_key, "BBB")
        ccc_book = get_order_book(api_url, api_key, "CCC")

        etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
        bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)
        ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

        # Check if we have valid market data
        if not all([etf_bid, etf_bid_qty, bbb_ask, bbb_ask_qty, ccc_ask, ccc_ask_qty]):
            print("[ULTRA-SHORT AAA] Insufficient market liquidity, waiting...")
            time.sleep(1)
            continue

        # Calculate trade quantity: min of all constraints
        trade_qty = min(etf_bid_qty, bbb_ask_qty, ccc_ask_qty, etf_sell_room, bbb_buy_room, ccc_buy_room, aaa_short_room)

        if trade_qty <= 0:
            print("[ULTRA-SHORT AAA] No tradeable quantity available")
            break

        print(f"[ULTRA-SHORT AAA] Executing ETF mechanism: trade_qty={trade_qty}")

        # Execute: Sell ETF, Buy BBB, Buy CCC
        orders = [
            {"symbol": "ETF", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": etf_bid},
            {"symbol": "BBB", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": bbb_ask},
            {"symbol": "CCC", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": ccc_ask},
        ]

        success = True
        for order in orders:
            try:
                api_post(api_url, "/api/v1/orders", api_key, order)
                print(f"[ULTRA-SHORT AAA] {order['side'].upper()} {order['quantity']} {order['symbol']} @ {order['price']}")
            except Exception as e:
                print(f"[ULTRA-SHORT AAA ERR] Failed {order['side']} {order['symbol']}: {e}")
                success = False

        if success:
            # Wait for fills
            time.sleep(0.2)
            # Create ETF from BBB+CCC we just bought
            # This consumes BBB+CCC and creates AAA (which nets against our short AAA from ETF sale)
            create_etf(api_url, api_key, trade_qty)
            print(f"[ULTRA-SHORT AAA] Net effect: -{trade_qty} AAA (BBB/CCC/ETF positions cancelled out)")

        time.sleep(0.5)

    print("[ULTRA-SHORT AAA] Strategy complete!")


def ultra_short_bbb(api_url: str, api_key: str) -> None:
    """
    Build maximum short position in BBB using ETF arbitrage mechanism.

    Strategy:
    1. Sell as much BBB directly (down to position limit -500)
    2. Loop: Sell ETF + Buy AAA + Buy CCC, then create ETF → net effect: -BBB
    3. Repeat until all position limits reached
    """
    POSITION_LIMIT = 500
    print("[ULTRA-SHORT BBB] Starting ultra-short BBB strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[ULTRA-SHORT BBB] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # Check if BBB is at negative limit
        if bbb_pos <= -POSITION_LIMIT:
            print(f"[ULTRA-SHORT BBB] BBB position limit reached ({bbb_pos}). Strategy complete.")
            break

        # Step 1: Sell BBB directly
        bbb_sell_room = bbb_pos - (-POSITION_LIMIT)
        if bbb_sell_room > 0:
            bbb_book = get_order_book(api_url, api_key, "BBB")
            bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)

            if bbb_bid and bbb_bid_qty:
                sell_qty = min(bbb_sell_room, bbb_bid_qty)
                order = {"symbol": "BBB", "side": "sell", "order_type": "limit", "quantity": sell_qty, "price": bbb_bid}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[ULTRA-SHORT BBB] Sold {sell_qty} BBB @ {bbb_bid}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[ULTRA-SHORT BBB ERR] Failed to sell BBB: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: Use ETF mechanism
        etf_sell_room = etf_pos - (-POSITION_LIMIT)
        aaa_buy_room = POSITION_LIMIT - aaa_pos
        ccc_buy_room = POSITION_LIMIT - ccc_pos
        bbb_short_room = bbb_pos - (-POSITION_LIMIT)

        if etf_sell_room <= 0 or aaa_buy_room <= 0 or ccc_buy_room <= 0 or bbb_short_room <= 0:
            print(f"[ULTRA-SHORT BBB] Position limits reached. ETF sell room={etf_sell_room}, AAA buy room={aaa_buy_room}, CCC buy room={ccc_buy_room}, BBB short room={bbb_short_room}")
            break

        # Get order books
        etf_book = get_order_book(api_url, api_key, "ETF")
        aaa_book = get_order_book(api_url, api_key, "AAA")
        ccc_book = get_order_book(api_url, api_key, "CCC")

        etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
        aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)
        ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

        if not all([etf_bid, etf_bid_qty, aaa_ask, aaa_ask_qty, ccc_ask, ccc_ask_qty]):
            print("[ULTRA-SHORT BBB] Insufficient market liquidity, waiting...")
            time.sleep(1)
            continue

        trade_qty = min(etf_bid_qty, aaa_ask_qty, ccc_ask_qty, etf_sell_room, aaa_buy_room, ccc_buy_room, bbb_short_room)

        if trade_qty <= 0:
            print("[ULTRA-SHORT BBB] No tradeable quantity available")
            break

        print(f"[ULTRA-SHORT BBB] Executing ETF mechanism: trade_qty={trade_qty}")

        # Execute: Sell ETF, Buy AAA, Buy CCC
        orders = [
            {"symbol": "ETF", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": etf_bid},
            {"symbol": "AAA", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": aaa_ask},
            {"symbol": "CCC", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": ccc_ask},
        ]

        success = True
        for order in orders:
            try:
                api_post(api_url, "/api/v1/orders", api_key, order)
                print(f"[ULTRA-SHORT BBB] {order['side'].upper()} {order['quantity']} {order['symbol']} @ {order['price']}")
            except Exception as e:
                print(f"[ULTRA-SHORT BBB ERR] Failed {order['side']} {order['symbol']}: {e}")
                success = False

        if success:
            time.sleep(0.2)
            create_etf(api_url, api_key, trade_qty)
            print(f"[ULTRA-SHORT BBB] Net effect: -{trade_qty} BBB (AAA/CCC/ETF positions cancelled out)")

        time.sleep(0.5)

    print("[ULTRA-SHORT BBB] Strategy complete!")


def ultra_short_ccc(api_url: str, api_key: str) -> None:
    """
    Build maximum short position in CCC using ETF arbitrage mechanism.

    Strategy:
    1. Sell as much CCC directly (down to position limit -500)
    2. Loop: Sell ETF + Buy AAA + Buy BBB, then create ETF → net effect: -CCC
    3. Repeat until all position limits reached
    """
    POSITION_LIMIT = 500
    print("[ULTRA-SHORT CCC] Starting ultra-short CCC strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[ULTRA-SHORT CCC] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # Check if CCC is at negative limit
        if ccc_pos <= -POSITION_LIMIT:
            print(f"[ULTRA-SHORT CCC] CCC position limit reached ({ccc_pos}). Strategy complete.")
            break

        # Step 1: Sell CCC directly
        ccc_sell_room = ccc_pos - (-POSITION_LIMIT)
        if ccc_sell_room > 0:
            ccc_book = get_order_book(api_url, api_key, "CCC")
            ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

            if ccc_bid and ccc_bid_qty:
                sell_qty = min(ccc_sell_room, ccc_bid_qty)
                order = {"symbol": "CCC", "side": "sell", "order_type": "limit", "quantity": sell_qty, "price": ccc_bid}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[ULTRA-SHORT CCC] Sold {sell_qty} CCC @ {ccc_bid}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[ULTRA-SHORT CCC ERR] Failed to sell CCC: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: Use ETF mechanism
        etf_sell_room = etf_pos - (-POSITION_LIMIT)
        aaa_buy_room = POSITION_LIMIT - aaa_pos
        bbb_buy_room = POSITION_LIMIT - bbb_pos
        ccc_short_room = ccc_pos - (-POSITION_LIMIT)

        if etf_sell_room <= 0 or aaa_buy_room <= 0 or bbb_buy_room <= 0 or ccc_short_room <= 0:
            print(f"[ULTRA-SHORT CCC] Position limits reached. ETF sell room={etf_sell_room}, AAA buy room={aaa_buy_room}, BBB buy room={bbb_buy_room}, CCC short room={ccc_short_room}")
            break

        # Get order books
        etf_book = get_order_book(api_url, api_key, "ETF")
        aaa_book = get_order_book(api_url, api_key, "AAA")
        bbb_book = get_order_book(api_url, api_key, "BBB")

        etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
        aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)
        bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)

        if not all([etf_bid, etf_bid_qty, aaa_ask, aaa_ask_qty, bbb_ask, bbb_ask_qty]):
            print("[ULTRA-SHORT CCC] Insufficient market liquidity, waiting...")
            time.sleep(1)
            continue

        trade_qty = min(etf_bid_qty, aaa_ask_qty, bbb_ask_qty, etf_sell_room, aaa_buy_room, bbb_buy_room, ccc_short_room)

        if trade_qty <= 0:
            print("[ULTRA-SHORT CCC] No tradeable quantity available")
            break

        print(f"[ULTRA-SHORT CCC] Executing ETF mechanism: trade_qty={trade_qty}")

        # Execute: Sell ETF, Buy AAA, Buy BBB
        orders = [
            {"symbol": "ETF", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": etf_bid},
            {"symbol": "AAA", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": aaa_ask},
            {"symbol": "BBB", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": bbb_ask},
        ]

        success = True
        for order in orders:
            try:
                api_post(api_url, "/api/v1/orders", api_key, order)
                print(f"[ULTRA-SHORT CCC] {order['side'].upper()} {order['quantity']} {order['symbol']} @ {order['price']}")
            except Exception as e:
                print(f"[ULTRA-SHORT CCC ERR] Failed {order['side']} {order['symbol']}: {e}")
                success = False

        if success:
            time.sleep(0.2)
            create_etf(api_url, api_key, trade_qty)
            print(f"[ULTRA-SHORT CCC] Net effect: -{trade_qty} CCC (AAA/BBB/ETF positions cancelled out)")

        time.sleep(0.5)

    print("[ULTRA-SHORT CCC] Strategy complete!")


# ----------------------------
# Exit Ultra-Long Strategies
# ----------------------------
def exit_ultra_long_aaa(api_url: str, api_key: str) -> None:
    """
    Exit ultra-long AAA position by selling all AAA holdings.

    Strategy:
    1. Sell all existing AAA position directly
    2. If we have BBB/CCC from the ultra-long process:
       - Create ETF from BBB+CCC (this produces more AAA)
       - Sell the resulting AAA
    3. Repeat until all positions are liquidated
    """
    print("[EXIT ULTRA-LONG AAA] Starting exit strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[EXIT ULTRA-LONG AAA] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # If all positions are zero or negative, we're done
        if aaa_pos <= 0 and bbb_pos <= 0 and ccc_pos <= 0 and etf_pos <= 0:
            print("[EXIT ULTRA-LONG AAA] All positions liquidated!")
            break

        # Step 1: Sell AAA directly
        if aaa_pos > 0:
            aaa_book = get_order_book(api_url, api_key, "AAA")
            aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)

            if aaa_bid and aaa_bid_qty:
                sell_qty = min(aaa_pos, aaa_bid_qty)
                order = {"symbol": "AAA", "side": "sell", "order_type": "limit", "quantity": sell_qty, "price": aaa_bid}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-LONG AAA] Sold {sell_qty} AAA @ {aaa_bid}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-LONG AAA ERR] Failed to sell AAA: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: If we have BBB and CCC, create ETF to produce AAA, then sell it
        if bbb_pos > 0 and ccc_pos > 0:
            create_qty = min(bbb_pos, ccc_pos, abs(aaa_pos) if aaa_pos < 0 else 1000)
            if create_qty > 0:
                create_etf(api_url, api_key, create_qty)
                time.sleep(0.2)
                # This produces AAA which we can then sell in next iteration

        # Step 3: If we have ETF, redeem it to get components
        if etf_pos > 0:
            redeem_etf(api_url, api_key, etf_pos)
            time.sleep(0.2)

        time.sleep(0.5)

    print("[EXIT ULTRA-LONG AAA] Exit complete!")


def exit_ultra_long_bbb(api_url: str, api_key: str) -> None:
    """
    Exit ultra-long BBB position by selling all BBB holdings.

    Strategy:
    1. Sell all existing BBB position directly
    2. If we have AAA/CCC from the ultra-long process:
       - Create ETF from AAA+CCC (this produces more BBB)
       - Sell the resulting BBB
    3. Repeat until all positions are liquidated
    """
    print("[EXIT ULTRA-LONG BBB] Starting exit strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[EXIT ULTRA-LONG BBB] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # If all positions are zero or negative, we're done
        if aaa_pos <= 0 and bbb_pos <= 0 and ccc_pos <= 0 and etf_pos <= 0:
            print("[EXIT ULTRA-LONG BBB] All positions liquidated!")
            break

        # Step 1: Sell BBB directly
        if bbb_pos > 0:
            bbb_book = get_order_book(api_url, api_key, "BBB")
            bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)

            if bbb_bid and bbb_bid_qty:
                sell_qty = min(bbb_pos, bbb_bid_qty)
                order = {"symbol": "BBB", "side": "sell", "order_type": "limit", "quantity": sell_qty, "price": bbb_bid}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-LONG BBB] Sold {sell_qty} BBB @ {bbb_bid}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-LONG BBB ERR] Failed to sell BBB: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: If we have AAA and CCC, create ETF to produce BBB, then sell it
        if aaa_pos > 0 and ccc_pos > 0:
            create_qty = min(aaa_pos, ccc_pos, abs(bbb_pos) if bbb_pos < 0 else 1000)
            if create_qty > 0:
                create_etf(api_url, api_key, create_qty)
                time.sleep(0.2)

        # Step 3: If we have ETF, redeem it to get components
        if etf_pos > 0:
            redeem_etf(api_url, api_key, etf_pos)
            time.sleep(0.2)

        time.sleep(0.5)

    print("[EXIT ULTRA-LONG BBB] Exit complete!")


def exit_ultra_long_ccc(api_url: str, api_key: str) -> None:
    """
    Exit ultra-long CCC position by selling all CCC holdings.

    Strategy:
    1. Sell all existing CCC position directly
    2. If we have AAA/BBB from the ultra-long process:
       - Create ETF from AAA+BBB (this produces more CCC)
       - Sell the resulting CCC
    3. Repeat until all positions are liquidated
    """
    print("[EXIT ULTRA-LONG CCC] Starting exit strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[EXIT ULTRA-LONG CCC] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # If all positions are zero or negative, we're done
        if aaa_pos <= 0 and bbb_pos <= 0 and ccc_pos <= 0 and etf_pos <= 0:
            print("[EXIT ULTRA-LONG CCC] All positions liquidated!")
            break

        # Step 1: Sell CCC directly
        if ccc_pos > 0:
            ccc_book = get_order_book(api_url, api_key, "CCC")
            ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

            if ccc_bid and ccc_bid_qty:
                sell_qty = min(ccc_pos, ccc_bid_qty)
                order = {"symbol": "CCC", "side": "sell", "order_type": "limit", "quantity": sell_qty, "price": ccc_bid}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-LONG CCC] Sold {sell_qty} CCC @ {ccc_bid}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-LONG CCC ERR] Failed to sell CCC: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: If we have AAA and BBB, create ETF to produce CCC, then sell it
        if aaa_pos > 0 and bbb_pos > 0:
            create_qty = min(aaa_pos, bbb_pos, abs(ccc_pos) if ccc_pos < 0 else 1000)
            if create_qty > 0:
                create_etf(api_url, api_key, create_qty)
                time.sleep(0.2)

        # Step 3: If we have ETF, redeem it to get components
        if etf_pos > 0:
            redeem_etf(api_url, api_key, etf_pos)
            time.sleep(0.2)

        time.sleep(0.5)

    print("[EXIT ULTRA-LONG CCC] Exit complete!")


# ----------------------------
# Exit Ultra-Short Strategies
# ----------------------------
def exit_ultra_short_aaa(api_url: str, api_key: str) -> None:
    """
    Exit ultra-short AAA position by buying back all AAA.

    Strategy:
    1. Buy back all short AAA position directly
    2. If we have long BBB/CCC positions from the ultra-short process:
       - Redeem ETF to get more AAA we can sell
       - Create ETF from BBB+CCC to consume them
    3. Repeat until all positions are closed
    """
    print("[EXIT ULTRA-SHORT AAA] Starting exit strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[EXIT ULTRA-SHORT AAA] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # If all positions are zero or positive AAA, we're done
        if aaa_pos >= 0 and bbb_pos <= 0 and ccc_pos <= 0 and etf_pos <= 0:
            print("[EXIT ULTRA-SHORT AAA] All short positions closed!")
            break

        # Step 1: Buy back AAA directly
        if aaa_pos < 0:
            aaa_book = get_order_book(api_url, api_key, "AAA")
            aaa_bid, aaa_bid_qty, aaa_ask, aaa_ask_qty = get_best_bid_ask(aaa_book)

            if aaa_ask and aaa_ask_qty:
                buy_qty = min(abs(aaa_pos), aaa_ask_qty)
                order = {"symbol": "AAA", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": aaa_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-SHORT AAA] Bought {buy_qty} AAA @ {aaa_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-SHORT AAA ERR] Failed to buy AAA: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: If we have BBB and CCC, create ETF to consume them
        if bbb_pos > 0 and ccc_pos > 0:
            create_qty = min(bbb_pos, ccc_pos)
            if create_qty > 0:
                create_etf(api_url, api_key, create_qty)
                time.sleep(0.2)

        # Step 3: If we have ETF, redeem it
        if etf_pos > 0:
            redeem_etf(api_url, api_key, etf_pos)
            time.sleep(0.2)

        # Step 4: If we have negative ETF, buy it back
        if etf_pos < 0:
            etf_book = get_order_book(api_url, api_key, "ETF")
            etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
            if etf_ask and etf_ask_qty:
                buy_qty = min(abs(etf_pos), etf_ask_qty)
                order = {"symbol": "ETF", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": etf_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-SHORT AAA] Bought {buy_qty} ETF @ {etf_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-SHORT AAA ERR] Failed to buy ETF: {e}")

        time.sleep(0.5)

    print("[EXIT ULTRA-SHORT AAA] Exit complete!")


def exit_ultra_short_bbb(api_url: str, api_key: str) -> None:
    """
    Exit ultra-short BBB position by buying back all BBB.

    Strategy:
    1. Buy back all short BBB position directly
    2. Clean up remaining positions using ETF create/redeem
    """
    print("[EXIT ULTRA-SHORT BBB] Starting exit strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[EXIT ULTRA-SHORT BBB] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # If all positions are zero or positive BBB, we're done
        if bbb_pos >= 0 and aaa_pos <= 0 and ccc_pos <= 0 and etf_pos <= 0:
            print("[EXIT ULTRA-SHORT BBB] All short positions closed!")
            break

        # Step 1: Buy back BBB directly
        if bbb_pos < 0:
            bbb_book = get_order_book(api_url, api_key, "BBB")
            bbb_bid, bbb_bid_qty, bbb_ask, bbb_ask_qty = get_best_bid_ask(bbb_book)

            if bbb_ask and bbb_ask_qty:
                buy_qty = min(abs(bbb_pos), bbb_ask_qty)
                order = {"symbol": "BBB", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": bbb_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-SHORT BBB] Bought {buy_qty} BBB @ {bbb_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-SHORT BBB ERR] Failed to buy BBB: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: If we have AAA and CCC, create ETF
        if aaa_pos > 0 and ccc_pos > 0:
            create_qty = min(aaa_pos, ccc_pos)
            if create_qty > 0:
                create_etf(api_url, api_key, create_qty)
                time.sleep(0.2)

        # Step 3: If we have ETF, redeem it
        if etf_pos > 0:
            redeem_etf(api_url, api_key, etf_pos)
            time.sleep(0.2)

        # Step 4: If we have negative ETF, buy it back
        if etf_pos < 0:
            etf_book = get_order_book(api_url, api_key, "ETF")
            etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
            if etf_ask and etf_ask_qty:
                buy_qty = min(abs(etf_pos), etf_ask_qty)
                order = {"symbol": "ETF", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": etf_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-SHORT BBB] Bought {buy_qty} ETF @ {etf_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-SHORT BBB ERR] Failed to buy ETF: {e}")

        time.sleep(0.5)

    print("[EXIT ULTRA-SHORT BBB] Exit complete!")


def exit_ultra_short_ccc(api_url: str, api_key: str) -> None:
    """
    Exit ultra-short CCC position by buying back all CCC.

    Strategy:
    1. Buy back all short CCC position directly
    2. Clean up remaining positions using ETF create/redeem
    """
    print("[EXIT ULTRA-SHORT CCC] Starting exit strategy...")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        print(f"[EXIT ULTRA-SHORT CCC] Positions: AAA={aaa_pos}, BBB={bbb_pos}, CCC={ccc_pos}, ETF={etf_pos}")

        # If all positions are zero or positive CCC, we're done
        if ccc_pos >= 0 and aaa_pos <= 0 and bbb_pos <= 0 and etf_pos <= 0:
            print("[EXIT ULTRA-SHORT CCC] All short positions closed!")
            break

        # Step 1: Buy back CCC directly
        if ccc_pos < 0:
            ccc_book = get_order_book(api_url, api_key, "CCC")
            ccc_bid, ccc_bid_qty, ccc_ask, ccc_ask_qty = get_best_bid_ask(ccc_book)

            if ccc_ask and ccc_ask_qty:
                buy_qty = min(abs(ccc_pos), ccc_ask_qty)
                order = {"symbol": "CCC", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": ccc_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-SHORT CCC] Bought {buy_qty} CCC @ {ccc_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-SHORT CCC ERR] Failed to buy CCC: {e}")

        # Refresh positions
        positions = get_positions(api_url, api_key)
        aaa_pos = positions.get("AAA", 0)
        bbb_pos = positions.get("BBB", 0)
        ccc_pos = positions.get("CCC", 0)
        etf_pos = positions.get("ETF", 0)

        # Step 2: If we have AAA and BBB, create ETF
        if aaa_pos > 0 and bbb_pos > 0:
            create_qty = min(aaa_pos, bbb_pos)
            if create_qty > 0:
                create_etf(api_url, api_key, create_qty)
                time.sleep(0.2)

        # Step 3: If we have ETF, redeem it
        if etf_pos > 0:
            redeem_etf(api_url, api_key, etf_pos)
            time.sleep(0.2)

        # Step 4: If we have negative ETF, buy it back
        if etf_pos < 0:
            etf_book = get_order_book(api_url, api_key, "ETF")
            etf_bid, etf_bid_qty, etf_ask, etf_ask_qty = get_best_bid_ask(etf_book)
            if etf_ask and etf_ask_qty:
                buy_qty = min(abs(etf_pos), etf_ask_qty)
                order = {"symbol": "ETF", "side": "buy", "order_type": "limit", "quantity": buy_qty, "price": etf_ask}
                try:
                    api_post(api_url, "/api/v1/orders", api_key, order)
                    print(f"[EXIT ULTRA-SHORT CCC] Bought {buy_qty} ETF @ {etf_ask}")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[EXIT ULTRA-SHORT CCC ERR] Failed to buy ETF: {e}")

        time.sleep(0.5)

    print("[EXIT ULTRA-SHORT CCC] Exit complete!")


# ----------------------------
# Market-making logic
# ----------------------------
def generate_fair_values(symbols: list[str]) -> dict[str, float]:
    fair = {}
    for s in symbols:
        fair[s] = round(random.uniform(90, 250), 2)
    return fair


def update_fair_values(fair: dict[str, float], drift_std: float = 0.5) -> None:
    for s in fair:
        fair[s] += random.gauss(0, drift_std)
        fair[s] = round(fair[s], 2)


def make_bid_ask_orders(symbol: str, fair_value: float) -> list[dict[str, Any]]:
    spread = random.uniform(0.1, 0.6)
    qty = random.randint(25, 50)

    bid_px = round(fair_value - spread / 2, 2)
    ask_px = round(fair_value + spread / 2, 2)

    return [
        {"symbol": symbol, "side": "buy", "order_type": "limit", "quantity": qty, "price": bid_px},
        {"symbol": symbol, "side": "sell", "order_type": "limit", "quantity": qty, "price": ask_px},
    ]


# ----------------------------
# Main trading loop
# ----------------------------
def market_making_loop(api_url: str, api_key: str, symbols: list[str], loop: bool = True):
    fair = generate_fair_values(symbols)
    print("Initial fair values:", fair)

    while True:
        update_fair_values(fair, drift_std=0.3)
        for sym in symbols:
            fair_value = fair[sym]
            orders = make_bid_ask_orders(sym, fair_value)
            for o in orders:
                place_order(api_url, api_key, o)
            print(f"[{sym}] fair={fair_value:.2f}\n")
            time.sleep(0.5)

        if not loop:
            break

        time.sleep(1)


# ----------------------------
# Entry point
# ----------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Automated Market Maker for CTC API")
    parser.add_argument("--api-url", default=os.environ.get("CTC_API_URL", "http://localhost:8000"))
    parser.add_argument("--api-key", default=os.environ.get("CTC_API_KEY") or os.environ.get("X_API_KEY"))
    parser.add_argument("--symbols", default="AAA,BBB,CCC,ETF", help="Comma-separated list of symbols")
    parser.add_argument("--loop", action="store_true", help="Continuously place orders")

    # Arbitrage strategy arguments
    parser.add_argument("--enable-arbitrage", action="store_true", help="Enable ETF arbitrage strategy")
    parser.add_argument("--arbitrage-only", action="store_true", help="Run only arbitrage strategy (no market making)")
    parser.add_argument("--arbitrage-interval", type=float, default=0.1, help="Arbitrage check interval in seconds")

    # Ultra-long strategy arguments
    parser.add_argument("--ultra-long-aaa", action="store_true", help="Execute ultra-long AAA strategy")
    parser.add_argument("--ultra-long-bbb", action="store_true", help="Execute ultra-long BBB strategy")
    parser.add_argument("--ultra-long-ccc", action="store_true", help="Execute ultra-long CCC strategy")

    # Ultra-short strategy arguments
    parser.add_argument("--ultra-short-aaa", action="store_true", help="Execute ultra-short AAA strategy")
    parser.add_argument("--ultra-short-bbb", action="store_true", help="Execute ultra-short BBB strategy")
    parser.add_argument("--ultra-short-ccc", action="store_true", help="Execute ultra-short CCC strategy")

    # Exit ultra-long strategy arguments
    parser.add_argument("--exit-ultra-long-aaa", action="store_true", help="Exit ultra-long AAA position")
    parser.add_argument("--exit-ultra-long-bbb", action="store_true", help="Exit ultra-long BBB position")
    parser.add_argument("--exit-ultra-long-ccc", action="store_true", help="Exit ultra-long CCC position")

    # Exit ultra-short strategy arguments
    parser.add_argument("--exit-ultra-short-aaa", action="store_true", help="Exit ultra-short AAA position")
    parser.add_argument("--exit-ultra-short-bbb", action="store_true", help="Exit ultra-short BBB position")
    parser.add_argument("--exit-ultra-short-ccc", action="store_true", help="Exit ultra-short CCC position")

    return parser.parse_args()


def main():
    args = parse_args()
    api_key = args.api_key or DEFAULT_API_KEY
    if not api_key:
        api_key = input("Enter API key: ").strip()
    if not api_key:
        print("API key required.")
        return 1

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    # Handle ultra-long strategies (execute and exit)
    if args.ultra_long_aaa:
        print("Executing ULTRA-LONG AAA strategy")
        ultra_long_aaa(args.api_url, api_key)
        return 0

    if args.ultra_long_bbb:
        print("Executing ULTRA-LONG BBB strategy")
        ultra_long_bbb(args.api_url, api_key)
        return 0

    if args.ultra_long_ccc:
        print("Executing ULTRA-LONG CCC strategy")
        ultra_long_ccc(args.api_url, api_key)
        return 0

    if args.exit_ultra_long_aaa:
        print("Exiting ULTRA-LONG AAA position")
        exit_ultra_long_aaa(args.api_url, api_key)
        return 0

    if args.exit_ultra_long_bbb:
        print("Exiting ULTRA-LONG BBB position")
        exit_ultra_long_bbb(args.api_url, api_key)
        return 0

    if args.exit_ultra_long_ccc:
        print("Exiting ULTRA-LONG CCC position")
        exit_ultra_long_ccc(args.api_url, api_key)
        return 0

    # Handle ultra-short strategies
    if args.ultra_short_aaa:
        print("Executing ULTRA-SHORT AAA strategy")
        ultra_short_aaa(args.api_url, api_key)
        return 0

    if args.ultra_short_bbb:
        print("Executing ULTRA-SHORT BBB strategy")
        ultra_short_bbb(args.api_url, api_key)
        return 0

    if args.ultra_short_ccc:
        print("Executing ULTRA-SHORT CCC strategy")
        ultra_short_ccc(args.api_url, api_key)
        return 0

    if args.exit_ultra_short_aaa:
        print("Exiting ULTRA-SHORT AAA position")
        exit_ultra_short_aaa(args.api_url, api_key)
        return 0

    if args.exit_ultra_short_bbb:
        print("Exiting ULTRA-SHORT BBB position")
        exit_ultra_short_bbb(args.api_url, api_key)
        return 0

    if args.exit_ultra_short_ccc:
        print("Exiting ULTRA-SHORT CCC position")
        exit_ultra_short_ccc(args.api_url, api_key)
        return 0

    # Run arbitrage-only mode
    if args.arbitrage_only:
        print("Running in ARBITRAGE-ONLY mode")
        arbitrage_loop(args.api_url, api_key, interval=args.arbitrage_interval)
        return 0

    # Run with both market making and arbitrage
    if args.enable_arbitrage:
        print("Starting CONCURRENT mode: Market Making + Arbitrage")
        # Start arbitrage in a separate thread
        arb_thread = threading.Thread(
            target=arbitrage_loop,
            args=(args.api_url, api_key, args.arbitrage_interval),
            daemon=True
        )
        arb_thread.start()
        print("[ARB] Arbitrage thread started")

    # Run market making in main thread
    market_making_loop(args.api_url, api_key, symbols, loop=args.loop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
