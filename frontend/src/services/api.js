/**
 * API Client for Trading Bot Backend
 *
 * This module provides functions to communicate with the Flask API server
 * for executing trading strategies and retrieving bot status.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// ----------------------------
// Health & Status
// ----------------------------

/**
 * Check API server health
 */
export const healthCheck = async () => {
  const response = await apiClient.get('/api/health');
  return response.data;
};

/**
 * Get bot status (running strategies, arbitrage status)
 */
export const getBotStatus = async () => {
  const response = await apiClient.get('/api/status');
  return response.data;
};

// ----------------------------
// Positions & Market Data
// ----------------------------

/**
 * Get current positions for all symbols
 */
export const getPositions = async () => {
  const response = await apiClient.get('/api/positions');
  return response.data;
};

/**
 * Get order book for a specific symbol
 * @param {string} symbol - Symbol name (AAA, BBB, CCC, ETF)
 */
export const getOrderBook = async (symbol) => {
  const response = await apiClient.get(`/api/orderbook/${symbol}`);
  return response.data;
};

// ----------------------------
// Ultra-Long Strategies
// ----------------------------

/**
 * Start ultra-long AAA strategy
 */
export const startUltraLongAAA = async () => {
  const response = await apiClient.post('/api/strategy/ultra-long-aaa');
  return response.data;
};

/**
 * Start ultra-long BBB strategy
 */
export const startUltraLongBBB = async () => {
  const response = await apiClient.post('/api/strategy/ultra-long-bbb');
  return response.data;
};

/**
 * Start ultra-long CCC strategy
 */
export const startUltraLongCCC = async () => {
  const response = await apiClient.post('/api/strategy/ultra-long-ccc');
  return response.data;
};

// ----------------------------
// Ultra-Short Strategies
// ----------------------------

/**
 * Start ultra-short AAA strategy
 */
export const startUltraShortAAA = async () => {
  const response = await apiClient.post('/api/strategy/ultra-short-aaa');
  return response.data;
};

/**
 * Start ultra-short BBB strategy
 */
export const startUltraShortBBB = async () => {
  const response = await apiClient.post('/api/strategy/ultra-short-bbb');
  return response.data;
};

/**
 * Start ultra-short CCC strategy
 */
export const startUltraShortCCC = async () => {
  const response = await apiClient.post('/api/strategy/ultra-short-ccc');
  return response.data;
};

// ----------------------------
// Exit Strategies
// ----------------------------

/**
 * Exit ultra-long AAA position
 */
export const exitLongAAA = async () => {
  const response = await apiClient.post('/api/strategy/exit-long-aaa');
  return response.data;
};

/**
 * Exit ultra-long BBB position
 */
export const exitLongBBB = async () => {
  const response = await apiClient.post('/api/strategy/exit-long-bbb');
  return response.data;
};

/**
 * Exit ultra-long CCC position
 */
export const exitLongCCC = async () => {
  const response = await apiClient.post('/api/strategy/exit-long-ccc');
  return response.data;
};

/**
 * Exit ultra-short AAA position
 */
export const exitShortAAA = async () => {
  const response = await apiClient.post('/api/strategy/exit-short-aaa');
  return response.data;
};

/**
 * Exit ultra-short BBB position
 */
export const exitShortBBB = async () => {
  const response = await apiClient.post('/api/strategy/exit-short-bbb');
  return response.data;
};

/**
 * Exit ultra-short CCC position
 */
export const exitShortCCC = async () => {
  const response = await apiClient.post('/api/strategy/exit-short-ccc');
  return response.data;
};

// ----------------------------
// Arbitrage Control
// ----------------------------

/**
 * Start arbitrage strategy
 * @param {number} interval - Check interval in seconds (default: 0.1)
 */
export const startArbitrage = async (interval = 0.1) => {
  const response = await apiClient.post('/api/arbitrage/start', { interval });
  return response.data;
};

/**
 * Stop arbitrage strategy
 */
export const stopArbitrage = async () => {
  const response = await apiClient.post('/api/arbitrage/stop');
  return response.data;
};

// ----------------------------
// Error Handling
// ----------------------------

/**
 * Handle API errors with user-friendly messages
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.error || error.response.data?.message || 'Server error occurred';
      throw new Error(message);
    } else if (error.request) {
      // Request made but no response
      throw new Error('Cannot connect to server. Make sure the API server is running.');
    } else {
      // Something else happened
      throw new Error(error.message || 'An unexpected error occurred');
    }
  }
);

export default apiClient;
