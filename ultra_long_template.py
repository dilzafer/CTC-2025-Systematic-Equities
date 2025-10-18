def ultra_long_XXX(api_url: str, api_key: str) -> None:
    """
    Build BALANCED long XXX position: +5000 XXX, -5000 YYY, -5000 ZZZ (market neutral).

    Strategy (executes all simultaneously for balanced positions):
    1. Buy XXX directly
    2. Sell YYY directly
    3. Sell ZZZ directly

    Target: +5000 XXX, -5000 YYY, -5000 ZZZ, 0 ETF
    """
    POSITION_LIMIT = 5000
    print("[ULTRA-LONG XXX] Starting BALANCED ultra-long XXX strategy...")
    print("[ULTRA-LONG XXX] Target: +5000 XXX, -5000 YYY, -5000 ZZZ")

    while True:
        # Get current positions
        positions = get_positions(api_url, api_key)
        xxx_pos = positions.get("XXX", 0)
        yyy_pos = positions.get("YYY", 0)
        zzz_pos = positions.get("ZZZ", 0)

        print(f"[ULTRA-LONG XXX] Current: XXX={xxx_pos}, YYY={yyy_pos}, ZZZ={zzz_pos}")

        # Calculate room for each position
        xxx_room = POSITION_LIMIT - xxx_pos  # Room to buy XXX
        yyy_room = yyy_pos - (-POSITION_LIMIT)  # Room to sell YYY
        zzz_room = zzz_pos - (-POSITION_LIMIT)  # Room to sell ZZZ

        # Check if all positions are at target
        if xxx_room <= 0 and yyy_room <= 0 and zzz_room <= 0:
            print(f"[ULTRA-LONG XXX] All positions at target! XXX={xxx_pos}, YYY={yyy_pos}, ZZZ={zzz_pos}")
            break

        # Get order books
        xxx_book = get_order_book(api_url, api_key, "XXX")
        yyy_book = get_order_book(api_url, api_key, "YYY")
        zzz_book = get_order_book(api_url, api_key, "ZZZ")

        xxx_bid, xxx_bid_qty, xxx_ask, xxx_ask_qty = get_best_bid_ask(xxx_book)
        yyy_bid, yyy_bid_qty, yyy_ask, yyy_ask_qty = get_best_bid_ask(yyy_book)
        zzz_bid, zzz_bid_qty, zzz_ask, zzz_ask_qty = get_best_bid_ask(zzz_book)

        # Check market data availability
        if not all([xxx_ask, xxx_ask_qty, yyy_bid, yyy_bid_qty, zzz_bid, zzz_bid_qty]):
            print("[ULTRA-LONG XXX] Insufficient market liquidity, waiting...")
            time.sleep(1)
            continue

        # Calculate BALANCED trade quantity (same quantity for all three)
        trade_qty = min(
            xxx_ask_qty if xxx_room > 0 else 999999,
            yyy_bid_qty if yyy_room > 0 else 999999,
            zzz_bid_qty if zzz_room > 0 else 999999,
            xxx_room if xxx_room > 0 else 0,
            yyy_room if yyy_room > 0 else 0,
            zzz_room if zzz_room > 0 else 0
        )

        if trade_qty <= 0:
            print("[ULTRA-LONG XXX] No tradeable quantity available")
            break

        print(f"[ULTRA-LONG XXX] Executing BALANCED trade: {trade_qty} units")

        # Execute all three orders SIMULTANEOUSLY for balanced positions
        orders = []
        if xxx_room > 0:
            orders.append({"symbol": "XXX", "side": "buy", "order_type": "limit", "quantity": trade_qty, "price": xxx_ask})
        if yyy_room > 0:
            orders.append({"symbol": "YYY", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": yyy_bid})
        if zzz_room > 0:
            orders.append({"symbol": "ZZZ", "side": "sell", "order_type": "limit", "quantity": trade_qty, "price": zzz_bid})

        # Place all orders concurrently
        def place_single_order(order):
            try:
                api_post(api_url, "/api/v1/orders", api_key, order)
                return (True, order)
            except Exception as e:
                print(f"[ULTRA-LONG XXX ERR] Failed {order['side']} {order['symbol']}: {e}")
                return (False, order)

        success = True
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(place_single_order, order) for order in orders]
            for future in as_completed(futures):
                result, order = future.result()
                if result:
                    print(f"[ULTRA-LONG XXX] {order['side'].upper()} {order['quantity']} {order['symbol']} @ {order['price']}")
                else:
                    success = False

        if not success:
            print("[ULTRA-LONG XXX] Some orders failed, retrying...")
            time.sleep(1)
            continue

        time.sleep(0.5)

    print("[ULTRA-LONG XXX] BALANCED strategy complete!")


# For BBB: Replace XXX with BBB, YYY with AAA, ZZZ with CCC
# For CCC: Replace XXX with CCC, YYY with AAA, ZZZ with BBB
