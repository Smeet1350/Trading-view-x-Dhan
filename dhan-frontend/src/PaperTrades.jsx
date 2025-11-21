// PaperTrades.jsx
import React, {useEffect, useState} from "react";
import axios from "axios";

const BASE_URL = import.meta.env?.VITE_API_URL || `http://${window.location.hostname}:8000`;

export default function PaperTrades() {
  const [enabled, setEnabled] = useState(false);
  const [trades, setTrades] = useState([]);
  const [pairedTrades, setPairedTrades] = useState([]);
  const [perSymbol, setPerSymbol] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () =>{
    try {
      const r = await axios.get(`${BASE_URL}/paper/status`);
      setEnabled(!!r.data.enabled);
    } catch (e) {}
  }
  const fetchTrades = async () =>{
    setLoading(true);
    try {
      const r = await axios.get(`${BASE_URL}/paper/trades`);
      if(r.data.status === "success"){
        setTrades(r.data.raw_trades || []);
        setPairedTrades(r.data.paired_trades || []);
        setPerSymbol(r.data.per_symbol || []);
        setSummary(r.data.overall || null);
      }
    } catch (e) {}
    setLoading(false);
  }

  useEffect(()=>{ 
    fetchStatus(); 
    fetchTrades(); 
    const id=setInterval(fetchTrades,10000); 
    return ()=>clearInterval(id); 
  },[]);

  const toggle = async (val) => {
    try {
      await axios.post(`${BASE_URL}/paper/toggle`, { enable: val });
      setEnabled(val);
    } catch (e) {
      console.error("Toggle failed:", e);
    }
  }

  const clearTrades = async () => {
    if (!confirm("Clear ALL paper trades? This cannot be undone.")) return;
    try {
      const r = await axios.post(`${BASE_URL}/paper/clear`);
      if (r.data?.status === "success") {
        alert("Paper trades cleared");
        fetchTrades();
      } else {
        alert("Clear failed");
      }
    } catch (err) {
      alert("Clear failed: " + (err?.message || err));
    }
  }

  return (
    <section className="card">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-lg text-indigo-300">📋 Paper Trading</h2>
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-1 rounded bg-red-600 text-sm"
            onClick={clearTrades}
          >
            Clear Trades
          </button>
          <label className="text-sm text-gray-400">Paper Mode</label>
          <button
            className={`px-3 py-1 rounded text-sm font-semibold ${enabled ? "bg-yellow-600" : "bg-gray-700"}`}
            onClick={() => toggle(!enabled)}
          >
            {enabled ? "ON" : "OFF"}
          </button>
        </div>
      </div>

      {enabled && (
        <div className="mt-2 bg-yellow-900 bg-opacity-30 border border-yellow-600 rounded p-2 text-sm text-yellow-200">
          ⚠️ Paper trading enabled - Webhooks will be simulated (no real orders)
        </div>
      )}

      <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
        <div className="bg-gray-800 p-3 rounded">
          <div className="text-gray-400 text-xs">Total P&L</div>
          <div className={`text-xl font-bold ${summary && summary.grand_total >= 0 ? "text-green-400" : "text-red-400"}`}>
            {summary ? `₹${summary.grand_total.toFixed(2)}` : "-"}
          </div>
        </div>
        <div className="bg-gray-800 p-3 rounded">
          <div className="text-gray-400 text-xs">Realized (Net)</div>
          <div className={`text-xl font-bold ${summary && summary.total_realized_net >= 0 ? "text-green-400" : "text-red-400"}`}>
            {summary ? `₹${summary.total_realized_net.toFixed(2)}` : "-"}
          </div>
        </div>
        <div className="bg-gray-800 p-3 rounded">
          <div className="text-gray-400 text-xs">Unrealized</div>
          <div className={`text-xl font-bold ${summary && summary.total_unrealized >= 0 ? "text-green-400" : "text-red-400"}`}>
            {summary ? `₹${summary.total_unrealized.toFixed(2)}` : "-"}
          </div>
        </div>
      </div>

      {/* Per-Symbol Summary */}
      {perSymbol.length > 0 && (
        <div className="mt-4">
          <h3 className="font-semibold text-sm mb-2">Open Positions</h3>
          <div className="overflow-auto max-h-48">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-300">
                  <th className="p-2">Symbol</th>
                  <th className="p-2">Position</th>
                  <th className="p-2">Avg Cost</th>
                  <th className="p-2">LTP</th>
                  <th className="p-2">Unrealized P&L</th>
                </tr>
              </thead>
              <tbody>
                {perSymbol.map((s, i) => (
                  <tr key={i} className="border-t border-gray-700">
                    <td className="p-2">{s.symbol}</td>
                    <td className="p-2">{s.position}</td>
                    <td className="p-2">₹{s.avg_cost.toFixed(2)}</td>
                    <td className="p-2">₹{s.ltp.toFixed(2)}</td>
                    <td className={`p-2 ${s.unrealized >= 0 ? "text-green-400" : "text-red-400"}`}>
                      ₹{s.unrealized.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Completed Round-trips */}
      <div className="mt-4">
        <h3 className="font-semibold text-sm mb-2">Completed Round-trips ({pairedTrades.length})</h3>
        {pairedTrades.length === 0 ? (
          <div className="text-gray-400 text-sm">No completed trades yet</div>
        ) : (
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-300">
                  <th className="p-2">Symbol</th>
                  <th className="p-2">Qty</th>
                  <th className="p-2">Entry</th>
                  <th className="p-2">Exit</th>
                  <th className="p-2">Gross P&L</th>
                  <th className="p-2">Fee</th>
                  <th className="p-2">Net P&L</th>
                </tr>
              </thead>
              <tbody>
                {pairedTrades.slice().reverse().map(p => (
                  <tr key={p.entry_trade_id + "-" + p.exit_trade_id} className="border-t border-gray-700">
                    <td className="p-2">{p.symbol}</td>
                    <td className="p-2">{p.qty}</td>
                    <td className="p-2">₹{p.entry_price.toFixed(2)}</td>
                    <td className="p-2">₹{p.exit_price.toFixed(2)}</td>
                    <td className={`p-2 ${p.pnl_gross >= 0 ? "text-green-400" : "text-red-400"}`}>
                      ₹{p.pnl_gross.toFixed(2)}
                    </td>
                    <td className="p-2">₹{p.fee}</td>
                    <td className={`p-2 ${p.pnl_net >= 0 ? "text-green-400" : "text-red-400"}`}>
                      ₹{p.pnl_net.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Trade History */}
      <div className="mt-4">
        <h3 className="font-semibold text-sm mb-2">All Trades ({trades.length})</h3>
        {loading ? (
          <div className="text-gray-400 text-sm">Loading...</div>
        ) : trades.length === 0 ? (
          <div className="text-gray-400 text-sm">No paper trades yet</div>
        ) : (
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-300">
                  <th className="p-2">Time</th>
                  <th className="p-2">Symbol</th>
                  <th className="p-2">Side</th>
                  <th className="p-2">Qty</th>
                  <th className="p-2">Type</th>
                  <th className="p-2">Exec Price</th>
                </tr>
              </thead>
              <tbody>
                {trades.slice().reverse().map(t=>(
                  <tr key={t.id} className="border-t border-gray-700">
                    <td className="p-2 text-xs">{new Date(t.ts_iso).toLocaleString()}</td>
                    <td className="p-2">{t.trading_symbol || t.security_id}</td>
                    <td className={`p-2 ${t.side === "BUY" ? "text-green-400" : "text-red-400"}`}>
                      {t.side}
                    </td>
                    <td className="p-2">{t.qty}</td>
                    <td className="p-2 text-xs">{t.order_type}</td>
                    <td className="p-2">₹{Number(t.exec_price).toFixed(2)}</td>
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


