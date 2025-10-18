// Cornell Trading Competition API Client
// Direct API calls - no backend needed

const CTC_API_URL = 'https://cornelltradingcompetition.org';
const CTC_API_KEY = 'xLw2g_6L6hqJ76LrmOfgJo_fKF6uNybtSx2HXHbXpiI';

const headers = {
  'X-API-Key': CTC_API_KEY,
  'Content-Type': 'application/json',
};

// ============== Core API Functions ==============

export const getPositions = async () => {
  const response = await fetch(`${CTC_API_URL}/api/v1/positions`, { headers });
  if (!response.ok) throw new Error('Failed to get positions');
  return response.json();
};

export const getOrderBook = async (symbol) => {
  const response = await fetch(`${CTC_API_URL}/api/v1/orderbook/${symbol}`, { headers });
  if (!response.ok) throw new Error(`Failed to get orderbook for ${symbol}`);
  return response.json();
};

export const placeOrder = async (order) => {
  const response = await fetch(`${CTC_API_URL}/api/v1/orders`, {
    method: 'POST',
    headers,
    body: JSON.stringify(order),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Order failed');
  }
  return response.json();
};

export const createETF = async (quantity) => {
  const response = await fetch(`${CTC_API_URL}/api/v1/etf/ETF/create`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ quantity }),
  });
  if (!response.ok) throw new Error('Failed to create ETF');
  return response.json();
};

export const redeemETF = async (quantity) => {
  const response = await fetch(`${CTC_API_URL}/api/v1/etf/ETF/redeem`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ quantity }),
  });
  if (!response.ok) throw new Error('Failed to redeem ETF');
  return response.json();
};

// ============== Helper Functions ==============

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const POSITION_LIMIT = 5000;
const COMPONENTS = ['AAA', 'BBB', 'CCC'];

// Check if positions would violate limits
const checkPositionLimits = (positions, orders) => {
  const projected = { ...positions };

  orders.forEach(order => {
    const change = order.side === 'buy' ? order.quantity : -order.quantity;
    projected[order.symbol] = (projected[order.symbol] || 0) + change;
  });

  for (const [symbol, pos] of Object.entries(projected)) {
    if (Math.abs(pos) > POSITION_LIMIT) {
      throw new Error(`Position limit exceeded for ${symbol}: ${pos}`);
    }
  }

  return true;
};

// ============== Arbitrage Strategy ==============

export const runArbitrage = async (onUpdate, stopSignal) => {
  console.log('[ARBITRAGE] Starting...');

  while (!stopSignal.stopped) {
    try {
      // Get all order books
      const [etfBook, aaaBook, bbbBook, cccBook, posData] = await Promise.all([
        getOrderBook('ETF'),
        getOrderBook('AAA'),
        getOrderBook('BBB'),
        getOrderBook('CCC'),
        getPositions(),
      ]);

      const positions = posData.positions || {};

      // Spread 1: ETF bid > sum(component asks)
      const etfBid = etfBook.bids?.[0]?.price;
      const aaaAsk = aaaBook.asks?.[0]?.price;
      const bbbAsk = bbbBook.asks?.[0]?.price;
      const cccAsk = cccBook.asks?.[0]?.price;

      if (etfBid && aaaAsk && bbbAsk && cccAsk) {
        const componentSum = aaaAsk + bbbAsk + cccAsk;
        if (etfBid > componentSum) {
          const qty = Math.min(
            etfBook.bids[0].quantity,
            aaaBook.asks[0].quantity,
            bbbBook.asks[0].quantity,
            cccBook.asks[0].quantity
          );

          const orders = [
            { symbol: 'ETF', side: 'sell', quantity: qty, order_type: 'market' },
            { symbol: 'AAA', side: 'buy', quantity: qty, order_type: 'market' },
            { symbol: 'BBB', side: 'buy', quantity: qty, order_type: 'market' },
            { symbol: 'CCC', side: 'buy', quantity: qty, order_type: 'market' },
          ];

          if (checkPositionLimits(positions, orders)) {
            await Promise.all(orders.map(placeOrder));
            onUpdate?.(`Spread1: ${qty} @ profit ${(etfBid - componentSum).toFixed(2)}`);
            await sleep(200);
            await createETF(qty); // Net positions to 0
          }
        }
      }

      // Spread 2: ETF ask < sum(component bids)
      const etfAsk = etfBook.asks?.[0]?.price;
      const aaaBid = aaaBook.bids?.[0]?.price;
      const bbbBid = bbbBook.bids?.[0]?.price;
      const cccBid = cccBook.bids?.[0]?.price;

      if (etfAsk && aaaBid && bbbBid && cccBid) {
        const componentSum = aaaBid + bbbBid + cccBid;
        if (etfAsk < componentSum) {
          const qty = Math.min(
            etfBook.asks[0].quantity,
            aaaBook.bids[0].quantity,
            bbbBook.bids[0].quantity,
            cccBook.bids[0].quantity
          );

          const orders = [
            { symbol: 'ETF', side: 'buy', quantity: qty, order_type: 'market' },
            { symbol: 'AAA', side: 'sell', quantity: qty, order_type: 'market' },
            { symbol: 'BBB', side: 'sell', quantity: qty, order_type: 'market' },
            { symbol: 'CCC', side: 'sell', quantity: qty, order_type: 'market' },
          ];

          if (checkPositionLimits(positions, orders)) {
            await Promise.all(orders.map(placeOrder));
            onUpdate?.(`Spread2: ${qty} @ profit ${(componentSum - etfAsk).toFixed(2)}`);
            await sleep(200);
            await redeemETF(qty); // Net positions to 0
          }
        }
      }

      await sleep(100);
    } catch (error) {
      console.error('[ARBITRAGE ERROR]', error);
      onUpdate?.(`Error: ${error.message}`);
    }
  }

  console.log('[ARBITRAGE] Stopped');
};

// ============== Ultra-Long Strategies ==============

export const ultraLongAAA = async () => {
  const posData = await getPositions();
  const positions = posData.positions || {};
  const currentAAA = positions.AAA || 0;
  const needed = POSITION_LIMIT - currentAAA;

  if (needed <= 0) throw new Error('Already at max long AAA position');

  // Step 1: Buy AAA directly
  const aaaBook = await getOrderBook('AAA');
  const directQty = Math.min(needed, aaaBook.asks?.[0]?.quantity || 0);

  if (directQty > 0) {
    await placeOrder({ symbol: 'AAA', side: 'buy', quantity: directQty, order_type: 'market' });
    await sleep(200);
  }

  // Step 2: Use ETF mechanism to build remaining position
  const remaining = needed - directQty;
  if (remaining > 0) {
    for (let i = 0; i < Math.ceil(remaining / 10); i++) {
      const qty = Math.min(10, remaining - i * 10);

      // Buy ETF, sell BBB+CCC, redeem ETF = net long AAA
      await placeOrder({ symbol: 'ETF', side: 'buy', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'BBB', side: 'sell', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'CCC', side: 'sell', quantity: qty, order_type: 'market' });
      await sleep(200);
      await redeemETF(qty);
      await sleep(100);
    }
  }

  return { success: true, quantity: needed };
};

export const ultraLongBBB = async () => {
  const posData = await getPositions();
  const positions = posData.positions || {};
  const currentBBB = positions.BBB || 0;
  const needed = POSITION_LIMIT - currentBBB;

  if (needed <= 0) throw new Error('Already at max long BBB position');

  const bbbBook = await getOrderBook('BBB');
  const directQty = Math.min(needed, bbbBook.asks?.[0]?.quantity || 0);

  if (directQty > 0) {
    await placeOrder({ symbol: 'BBB', side: 'buy', quantity: directQty, order_type: 'market' });
    await sleep(200);
  }

  const remaining = needed - directQty;
  if (remaining > 0) {
    for (let i = 0; i < Math.ceil(remaining / 10); i++) {
      const qty = Math.min(10, remaining - i * 10);
      await placeOrder({ symbol: 'ETF', side: 'buy', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'AAA', side: 'sell', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'CCC', side: 'sell', quantity: qty, order_type: 'market' });
      await sleep(200);
      await redeemETF(qty);
      await sleep(100);
    }
  }

  return { success: true, quantity: needed };
};

export const ultraLongCCC = async () => {
  const posData = await getPositions();
  const positions = posData.positions || {};
  const currentCCC = positions.CCC || 0;
  const needed = POSITION_LIMIT - currentCCC;

  if (needed <= 0) throw new Error('Already at max long CCC position');

  const cccBook = await getOrderBook('CCC');
  const directQty = Math.min(needed, cccBook.asks?.[0]?.quantity || 0);

  if (directQty > 0) {
    await placeOrder({ symbol: 'CCC', side: 'buy', quantity: directQty, order_type: 'market' });
    await sleep(200);
  }

  const remaining = needed - directQty;
  if (remaining > 0) {
    for (let i = 0; i < Math.ceil(remaining / 10); i++) {
      const qty = Math.min(10, remaining - i * 10);
      await placeOrder({ symbol: 'ETF', side: 'buy', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'AAA', side: 'sell', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'BBB', side: 'sell', quantity: qty, order_type: 'market' });
      await sleep(200);
      await redeemETF(qty);
      await sleep(100);
    }
  }

  return { success: true, quantity: needed };
};

// ============== Ultra-Short Strategies ==============

export const ultraShortAAA = async () => {
  const posData = await getPositions();
  const positions = posData.positions || {};
  const currentAAA = positions.AAA || 0;
  const needed = Math.abs(-POSITION_LIMIT - currentAAA);

  if (needed <= 0) throw new Error('Already at max short AAA position');

  const aaaBook = await getOrderBook('AAA');
  const directQty = Math.min(needed, aaaBook.bids?.[0]?.quantity || 0);

  if (directQty > 0) {
    await placeOrder({ symbol: 'AAA', side: 'sell', quantity: directQty, order_type: 'market' });
    await sleep(200);
  }

  const remaining = needed - directQty;
  if (remaining > 0) {
    for (let i = 0; i < Math.ceil(remaining / 10); i++) {
      const qty = Math.min(10, remaining - i * 10);

      // Sell ETF, buy BBB+CCC, create ETF = net short AAA
      await placeOrder({ symbol: 'ETF', side: 'sell', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'BBB', side: 'buy', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'CCC', side: 'buy', quantity: qty, order_type: 'market' });
      await sleep(200);
      await createETF(qty);
      await sleep(100);
    }
  }

  return { success: true, quantity: needed };
};

export const ultraShortBBB = async () => {
  const posData = await getPositions();
  const positions = posData.positions || {};
  const currentBBB = positions.BBB || 0;
  const needed = Math.abs(-POSITION_LIMIT - currentBBB);

  if (needed <= 0) throw new Error('Already at max short BBB position');

  const bbbBook = await getOrderBook('BBB');
  const directQty = Math.min(needed, bbbBook.bids?.[0]?.quantity || 0);

  if (directQty > 0) {
    await placeOrder({ symbol: 'BBB', side: 'sell', quantity: directQty, order_type: 'market' });
    await sleep(200);
  }

  const remaining = needed - directQty;
  if (remaining > 0) {
    for (let i = 0; i < Math.ceil(remaining / 10); i++) {
      const qty = Math.min(10, remaining - i * 10);
      await placeOrder({ symbol: 'ETF', side: 'sell', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'AAA', side: 'buy', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'CCC', side: 'buy', quantity: qty, order_type: 'market' });
      await sleep(200);
      await createETF(qty);
      await sleep(100);
    }
  }

  return { success: true, quantity: needed };
};

export const ultraShortCCC = async () => {
  const posData = await getPositions();
  const positions = posData.positions || {};
  const currentCCC = positions.CCC || 0;
  const needed = Math.abs(-POSITION_LIMIT - currentCCC);

  if (needed <= 0) throw new Error('Already at max short CCC position');

  const cccBook = await getOrderBook('CCC');
  const directQty = Math.min(needed, cccBook.bids?.[0]?.quantity || 0);

  if (directQty > 0) {
    await placeOrder({ symbol: 'CCC', side: 'sell', quantity: directQty, order_type: 'market' });
    await sleep(200);
  }

  const remaining = needed - directQty;
  if (remaining > 0) {
    for (let i = 0; i < Math.ceil(remaining / 10); i++) {
      const qty = Math.min(10, remaining - i * 10);
      await placeOrder({ symbol: 'ETF', side: 'sell', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'AAA', side: 'buy', quantity: qty, order_type: 'market' });
      await placeOrder({ symbol: 'BBB', side: 'buy', quantity: qty, order_type: 'market' });
      await sleep(200);
      await createETF(qty);
      await sleep(100);
    }
  }

  return { success: true, quantity: needed };
};
