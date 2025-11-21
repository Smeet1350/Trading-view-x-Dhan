// PaperTrading.jsx
import React, { useEffect, useState } from "react";
import axios from "axios";

const BASE_URL = import.meta.env?.VITE_API_URL || `http://${window.location.hostname}:8000`;

export default function PaperTrading() {
  const [enabled, setEnabled] = useState(false);
  const [charge, setCharge] = useState(600);
  const [buySlippage, setBuySlippage] = useState(5);
  const [sellSlippage, setSellSlippage] = useState(7);
  const [trades, setTrades] = useState([]);
  const [cumNet, setCumNet] = useState(0);
  const [cumGross, setCumGross] = useState(0);
  const [loading, setLoading] = useState(false);


  const fetchEnabled = async () => {
    try {
      const r = await axios.get(`${BASE_URL}/paper/enabled`);
      setEnabled(!!r.data.enabled);
      setCharge(r.data.charge_per_round_trip || 600);
      setBuySlippage(r.data.buy_slippage || 5);
      setSellSlippage(r.data.sell_slippage || 7);
    } catch (e) {
      console.error("Failed to fetch paper enabled status", e);
    }
  };

  const fetchTrades = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${BASE_URL}/paper/trades`);
      if (r.data) {
        setTrades(r.data.trades || []);
        setCumNet(r.data.cumulative_net || 0);
        setCumGross(r.data.cumulative_gross || 0);
      }
    } catch (e) {
      console.error("Failed to fetch trades", e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchEnabled();
    fetchTrades();
    const id = setInterval(fetchTrades, 10000);
    return () => clearInterval(id);
  }, []);

  const toggleEnabled = async () => {
    try {
      const newVal = !enabled;
      await axios.post(`${BASE_URL}/paper/enabled?value=${newVal}`);
      setEnabled(newVal);
    } catch (e) {
      alert("Toggle failed: " + (e?.message || e));
    }
  };

  const clearTrades = async () => {
    if (!confirm("Clear ALL paper trades? This cannot be undone.")) return;
    try {
      await axios.post(`${BASE_URL}/paper/clear`);
      alert("Paper trades cleared");
      fetchTrades();
    } catch (e) {
      alert("Clear failed: " + (e?.message || e));
    }
  };


  const openTrades = trades.filter(t => t.exit_price === null || t.exit_price === undefined);
  const closedTrades = trades.filter(t => t.exit_price !== null && t.exit_price !== undefined);

  return (
    <section className="card">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-lg text-indigo-300">📋 Paper Trading</h2>
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-1 rounded bg-red-600 text-sm"
            onClick={clearTrades}
          >
            Clear All
          </button>
          <label className="text-sm text-gray-400">Paper Mode</label>
          <button
            className={`px-3 py-1 rounded text-sm font-semibold ${enabled ? "bg-yellow-600" : "bg-gray-700"}`}
            onClick={toggleEnabled}
          >
            {enabled ? "ON" : "OFF"}
          </button>
        </div>
      </div>

      {enabled && (
        <div className="mb-3 bg-yellow-900 bg-opacity-30 border border-yellow-600 rounded p-2 text-sm text-yellow-200">
          ⚠️ Paper trading enabled - Webhooks will be simulated (no real orders). Charge: ₹{charge} per round-trip.
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 text-sm mb-4">
        <div className="bg-gray-800 p-3 rounded">
          <div className="text-gray-400 text-xs">Cumulative Net P&L</div>
          <div className={`text-xl font-bold ${cumNet >= 0 ? "text-green-400" : "text-red-400"}`}>
            ₹{cumNet.toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-800 p-3 rounded">
          <div className="text-gray-400 text-xs">Cumulative Gross P&L</div>
          <div className={`text-xl font-bold ${cumGross >= 0 ? "text-green-400" : "text-red-400"}`}>
            ₹{cumGross.toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-800 p-3 rounded">
          <div className="text-gray-400 text-xs">Open / Closed Trades</div>
          <div className="text-xl font-bold text-gray-200">
            {openTrades.length} / {closedTrades.length}
          </div>
        </div>
      </div>


      {/* Open Trades */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold mb-2">Open Trades ({openTrades.length})</h3>
        {openTrades.length === 0 ? (
          <div className="text-gray-400 text-sm">No open trades</div>
        ) : (
          <div className="overflow-auto max-h-64">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-300">
                  <th className="p-2">ID</th>
                  <th className="p-2">Symbol</th>
                  <th className="p-2">Side</th>
                  <th className="p-2">Qty</th>
                  <th className="p-2">Entry Price</th>
                  <th className="p-2">Entry Time</th>
                  <th className="p-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {openTrades.map((t) => (
                  <tr key={t.id} className="border-t border-gray-700">
                    <td className="p-2">{t.id}</td>
                    <td className="p-2">{t.trading_symbol || t.symbol || t.security_id}</td>
                    <td className={`p-2 ${t.side === "BUY" ? "text-green-400" : "text-red-400"}`}>
                      {t.side}
                    </td>
                    <td className="p-2">{t.qty}</td>
                    <td className="p-2">₹{Number(t.entry_price || t.exec_price || 0).toFixed(2)}</td>
                    <td className="p-2 text-xs">{new Date(t.entry_ts || t.ts_iso).toLocaleString()}</td>
                    <td className="p-2">
                      <span className="bg-yellow-600 px-2 py-1 rounded text-xs">
                        {t.status || "OPEN"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Closed Trades */}
      <div>
        <h3 className="text-sm font-semibold mb-2">Closed Trades ({closedTrades.length})</h3>
        {loading ? (
          <div className="text-gray-400 text-sm">Loading...</div>
        ) : closedTrades.length === 0 ? (
          <div className="text-gray-400 text-sm">No closed trades yet</div>
        ) : (
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-300">
                  <th className="p-2">Symbol</th>
                  <th className="p-2">Side</th>
                  <th className="p-2">Qty</th>
                  <th className="p-2">Entry Price</th>
                  <th className="p-2">Exit Price</th>
                  <th className="p-2">Gross P&L</th>
                  <th className="p-2">Charge</th>
                  <th className="p-2">Net P&L</th>
                  <th className="p-2">Source</th>
                  <th className="p-2">Exit Time</th>
                </tr>
              </thead>
              <tbody>
                {closedTrades.map((t) => (
                  <tr key={t.id} className="border-t border-gray-700">
                    <td className="p-2">{t.trading_symbol || t.symbol || t.security_id}</td>
                    <td className={`p-2 ${t.side === "BUY" ? "text-green-400" : "text-red-400"}`}>
                      {t.side}
                    </td>
                    <td className="p-2">{t.qty}</td>
                    <td className="p-2">₹{Number(t.entry_price || 0).toFixed(2)}</td>
                    <td className="p-2">₹{Number(t.exit_price || 0).toFixed(2)}</td>
                    <td className={`p-2 ${(t.gross_pnl || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                      ₹{Number(t.gross_pnl || 0).toFixed(2)}
                    </td>
                    <td className="p-2">₹{Number(t.charge || 0).toFixed(2)}</td>
                    <td className={`p-2 font-semibold ${(t.net_pnl || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                      ₹{Number(t.net_pnl || 0).toFixed(2)}
                    </td>
                    <td className="p-2 text-xs">{t.price_source || "alert"}</td>
                    <td className="p-2 text-xs">{new Date(t.exit_ts).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

