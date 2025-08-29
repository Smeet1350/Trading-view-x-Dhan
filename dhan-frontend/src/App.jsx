import React, { useEffect, useRef, useState } from "react";
import axios from "axios";

// Back-end must run here:
const BASE_URL = "http://127.0.0.1:8000";

function safeMsg(x) {
  if (!x && x !== 0) return "";
  if (typeof x === "string") return x;
  if (typeof x === "object") {
    if (x.message) return String(x.message);
    try { return JSON.stringify(x); } catch { return String(x); }
  }
  return String(x);
}

export default function App() {
  // Connection / global
  const [status, setStatus] = useState("Checking...");
  const [statusError, setStatusError] = useState(null);
  const [notif, setNotif] = useState(null);

  // Data
  const [funds, setFunds] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);

  // Place order form
  const [segment, setSegment] = useState("NSE_EQ");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedInstrument, setSelectedInstrument] = useState(null);
  const [qty, setQty] = useState(1);
  const [side, setSide] = useState("BUY");
  const [orderType, setOrderType] = useState("MARKET");
  const [price, setPrice] = useState("");
  const [productType, setProductType] = useState("DELIVERY");
  const [validity, setValidity] = useState("DAY");

  // UI state
  const [error, setError] = useState(null);
  const [placing, setPlacing] = useState(false);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [marketNotice, setMarketNotice] = useState("");

  const pollRef = useRef(null);
  const searchDebounceRef = useRef(null);

  const api = axios.create({ baseURL: BASE_URL, timeout: 15000 });
  const log = (...args) => console.log("[UI]", ...args);
  const toast = (m) => { setNotif(m); setTimeout(() => setNotif(null), 4000); };

  // Fetch all core data
  const fetchAll = async () => {
    try {
      log("GET /status");
      const s = await api.get("/status");
      if (s.data?.status === "ok" || s.data?.status === "degraded") {
        const okDB = s.data?.instruments_db_current_today;
        const okBroker = s.data?.broker_ready;
        setStatus(
          `Connected ${okBroker ? "✅" : "⚠️"} ${okDB ? "" : "(Instrument DB outdated)"}`
        );
        setStatusError(s.data?.message || null);
      } else {
        setStatus("Not Connected ❌");
        setStatusError(s.data?.message || "Backend not-ok");
      }

      log("GET /funds");
      const f = await api.get("/funds");
      setFunds(f.data?.funds ?? null);

      log("GET /holdings");
      const h = await api.get("/holdings");
      setHoldings(h.data?.holdings ?? []);

      log("GET /positions");
      const p = await api.get("/positions");
      setPositions(p.data?.positions ?? []);
    } catch (err) {
      setStatus("Not Connected ❌");
      setStatusError(safeMsg(err.message || err));
      setError("Backend unreachable: " + safeMsg(err.message || err));
    }
  };

  useEffect(() => {
    fetchAll();
    pollRef.current = setInterval(fetchAll, 10000);
    return () => clearInterval(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Orders list
  const fetchOrders = async () => {
    setLoadingOrders(true);
    try {
      log("GET /orders");
      const r = await api.get("/orders");
      setOrders(r.data?.orders ?? []);
    } catch (e) {
      setOrders([]);
      setError("Error fetching orders: " + safeMsg(e.message || e));
    } finally {
      setLoadingOrders(false);
    }
  };
  useEffect(() => {
    fetchOrders();
    const id = setInterval(fetchOrders, 10000);
    return () => clearInterval(id);
  }, []);

  // Symbol search (debounced)
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(async () => {
      try {
        log("GET /symbol-search", searchQuery, segment);
        const res = await api.get("/symbol-search", { params: { query: searchQuery, segment } });
        setSearchResults(res.data?.results ?? []);
      } catch {
        setSearchResults([]);
      }
    }, 300);
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, segment]);

  const pickInstrument = (inst) => {
    setSelectedInstrument(inst);
    setSearchQuery(inst.tradingSymbol + (inst.expiry ? ` ${inst.expiry}` : ""));
    setSearchResults([]);
  };

  // Place order
  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    setPlacing(true);
    setError(null);
    setMarketNotice("");
    try {
      if (!selectedInstrument) {
        toast("Please select an instrument from search results first.");
        setPlacing(false);
        return;
      }
      const params = {
        symbol: selectedInstrument.tradingSymbol,
        segment,
        side,
        qty,
        order_type: orderType,
        price: orderType === "LIMIT" ? parseFloat(price || 0) : 0,
        product_type: productType,         // "DELIVERY" or "INTRADAY" is fine; backend maps to CNC/INTRA
        validity,
        security_id: selectedInstrument.securityId,   // ← IMPORTANT
      };
      log("POST /order/place", params);
      const res = await api.post("/order/place", null, { params });
      const msg = res.data?.message || res.data?.broker?.message || "Order failed";
      if (res.data?.status !== "success") {
        setError("Order failed: " + msg);
        console.log("order/place failed:", res.data); // keep for debugging
      } else {
        // success toast, then refresh orders
        toast("✅ " + msg);
        setMarketNotice(res.data?.broker?.message || "");
        await fetchOrders();
        await fetchAll();
      }
    } catch (e1) {
      const msg = "Error placing order: " + safeMsg(e1.message || e1);
      setError(msg);
      toast("💥 " + msg);
      log("order/place exception", e1);
    } finally {
      setPlacing(false);
    }
  };

  const handleCancel = async (orderId) => {
    if (!orderId) return;
    if (!window.confirm(`Cancel order ${orderId}?`)) return;
    try {
      log("POST /order/cancel", orderId);
      const res = await api.post("/order/cancel", null, { params: { order_id: orderId } });
      if (res.data?.status === "success") {
        toast("Order cancelled ✅");
        fetchOrders();
      } else {
        toast("Cancel failed: " + (res.data?.message || "Unknown"));
      }
    } catch (e) {
      toast("Cancel error: " + safeMsg(e.message || e));
    }
  };

  const money = (v) => (v === null || v === undefined ? "-" : Number(v).toFixed(2));

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Dhan Dashboard</h1>
          <div className="text-right">
            <div className="text-sm">Connection</div>
            <div className={`font-mono ${status.includes("Connected") ? "text-green-400" : "text-red-400"}`}>
              {status}
            </div>
            {statusError && <div className="text-xs text-yellow-300 mt-1">{statusError}</div>}
          </div>
        </header>

        {notif && <div className="bg-gray-800 p-3 rounded text-sm">{notif}</div>}

        {error && (
          <div className="bg-red-800 p-3 rounded text-sm">
            <strong>Error:</strong> {safeMsg(error)}
          </div>
        )}

        {/* Funds */}
        <section className="card">
          <h2 className="font-semibold text-lg text-green-300">💰 Funds</h2>
          {funds ? (
            <div className="grid grid-cols-2 gap-4 mt-2 text-sm">
              <div>Available: ₹{money(funds.availabelBalance ?? funds.available ?? funds.avail ?? funds.availableBalance)}</div>
              <div>Withdrawable: ₹{money(funds.withdrawableBalance ?? funds.withdrawable ?? funds.withdraw)}</div>
              <div>SOD Limit: ₹{money(funds.sodLimit ?? funds.sodLimit)}</div>
              <div>Collateral: ₹{money(funds.collateralAmount ?? funds.collateral)}</div>
            </div>
          ) : (
            <div className="text-gray-400 text-sm mt-2">Funds not available</div>
          )}
        </section>

        {/* Holdings */}
        <section className="card">
          <h2 className="font-semibold text-lg text-yellow-300">📦 Holdings</h2>
          {holdings.length > 0 ? (
            <div className="overflow-auto mt-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-300">
                    <th className="p-2">Symbol</th>
                    <th className="p-2">Qty</th>
                    <th className="p-2">Avg</th>
                    <th className="p-2">LTP</th>
                    <th className="p-2">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h, i) => {
                    const avg = parseFloat(h.avgCostPrice ?? h.averagePrice ?? 0);
                    const ltp = parseFloat(h.lastTradedPrice ?? h.ltp ?? 0);
                    const qtyv = parseFloat(h.totalQty ?? h.quantity ?? 0);
                    const pnl = (ltp - avg) * qtyv;
                    return (
                      <tr key={i} className="border-t border-gray-700">
                        <td className="p-2">{h.tradingSymbol}</td>
                        <td className="p-2">{qtyv}</td>
                        <td className="p-2">₹{money(avg)}</td>
                        <td className="p-2">₹{money(ltp)}</td>
                        <td className={`p-2 ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>₹{money(pnl)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : <div className="text-gray-400 mt-2">No holdings found</div>}
        </section>

        {/* Positions */}
        <section className="card">
          <h2 className="font-semibold text-lg text-purple-300">📌 Positions</h2>
          {positions.length > 0 ? (
            <div className="overflow-auto mt-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-300">
                    <th className="p-2">Symbol</th>
                    <th className="p-2">Qty</th>
                    <th className="p-2">Avg</th>
                    <th className="p-2">LTP</th>
                    <th className="p-2">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p, i) => {
                    const avg = parseFloat(p.buyAvg ?? p.avgPrice ?? 0);
                    const ltp = parseFloat(p.ltp ?? p.lastTradedPrice ?? 0);
                    const qtyv = parseFloat(p.netQty ?? p.quantity ?? 0);
                    const pnl = (ltp - avg) * qtyv;
                    return (
                      <tr key={i} className="border-t border-gray-700">
                        <td className="p-2">{p.tradingSymbol}</td>
                        <td className="p-2">{qtyv}</td>
                        <td className="p-2">₹{money(avg)}</td>
                        <td className="p-2">₹{money(ltp)}</td>
                        <td className={`p-2 ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>₹{money(pnl)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : <div className="text-gray-400 mt-2">No open positions</div>}
        </section>

        {/* Orders & Place Order */}
        <section className="card">
          <div className="flex items-start justify-between gap-4">
            <h2 className="font-semibold text-lg text-blue-300">📝 Orders</h2>
            <div className="text-sm">
              <button className="btn mr-2" onClick={fetchOrders} disabled={loadingOrders}>
                Refresh Orders
              </button>
              <button className="btn" onClick={() => { setOrders([]); fetchOrders(); }}>
                Clear & Refresh
              </button>
            </div>
          </div>

          {/* Place order form */}
          <form className="mt-3 grid grid-cols-1 md:grid-cols-6 gap-2 items-end" onSubmit={handlePlaceOrder}>
            <div className="md:col-span-2">
              <label className="block text-xs text-gray-400">Segment</label>
              <select className="select" value={segment} onChange={(e) => setSegment(e.target.value)}>
                <option value="NSE_EQ">NSE Equity</option>
                <option value="BSE_EQ">BSE Equity</option>
                <option value="NSE_FNO">NSE F&O</option>
                <option value="MCX">MCX</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs text-gray-400">Symbol / Search</label>
              <input
                type="text"
                className="input"
                placeholder="Type symbol (e.g. TCS or NIFTY24SEP...)"
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setSelectedInstrument(null); }}
              />
              {searchResults.length > 0 && (
                <ul className="bg-gray-800 mt-1 rounded max-h-44 overflow-auto border border-gray-700">
                  {searchResults.map((s) => (
                    <li key={s.securityId} className="p-2 hover:bg-gray-700 cursor-pointer text-sm" onClick={() => pickInstrument(s)}>
                      <div className="flex justify-between">
                        <div>{s.tradingSymbol} {s.expiry ? `(${s.expiry})` : ""}</div>
                        <div className="text-xs text-gray-400">ID:{s.securityId}</div>
                      </div>
                      <div className="text-xs text-gray-400">{s.segment} • lot: {s.lotSize}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <label className="block text-xs text-gray-400">Qty</label>
              <input type="number" min="1" value={qty} onChange={(e) => setQty(Number(e.target.value || 1))} className="input" />
            </div>

            <div>
              <label className="block text-xs text-gray-400">Side</label>
              <select value={side} onChange={(e) => setSide(e.target.value)} className="select">
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-400">Order Type</label>
              <select value={orderType} onChange={(e) => setOrderType(e.target.value)} className="select">
                <option value="MARKET">MARKET</option>
                <option value="LIMIT">LIMIT</option>
              </select>
            </div>

            {orderType === "LIMIT" && (
              <div className="md:col-span-1">
                <label className="block text-xs text-gray-400">Limit Price</label>
                <input type="number" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} className="input" />
              </div>
            )}

            <div className="md:col-span-6 flex gap-2 mt-2">
              <select value={productType} onChange={(e)=>setProductType(e.target.value)} className="select">
                <option value="DELIVERY">DELIVERY/CNC</option>
                <option value="INTRADAY">INTRADAY/MIS</option>
              </select>
              <select value={validity} onChange={(e)=>setValidity(e.target.value)} className="select">
                <option value="DAY">DAY</option>
                <option value="IOC">IOC</option>
              </select>
              <button type="submit" className="bg-green-600 px-4 py-2 rounded hover:bg-green-700" disabled={placing || !selectedInstrument?.securityId}>
                {placing ? "Placing..." : "Place Order"}
              </button>

              <div className="ml-auto text-sm text-gray-400">
                {selectedInstrument ? (
                  <div>
                    <div><strong>Selected:</strong> {selectedInstrument.tradingSymbol} (ID: {selectedInstrument.securityId})</div>
                    <div className="text-xs">Segment: {selectedInstrument.segment} • lot: {selectedInstrument.lotSize}</div>
                  </div>
                ) : (
                  <div className="text-xs">No instrument selected</div>
                )}
              </div>
            </div>
          </form>

          {marketNotice && <div className="mt-2 text-yellow-300 text-sm">{marketNotice}</div>}
          <hr className="my-3 border-gray-700" />

          {/* Order Book */}
          <div>
            <h3 className="font-semibold">Order Book</h3>
            {loadingOrders ? (
              <div className="text-sm text-gray-400 mt-2">Loading orders...</div>
            ) : orders && orders.length > 0 ? (
              <div className="overflow-auto mt-2">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-300">
                      <th className="p-2">Order ID</th>
                      <th className="p-2">Symbol</th>
                      <th className="p-2">Side</th>
                      <th className="p-2">Qty</th>
                      <th className="p-2">Status</th>
                      <th className="p-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((o, i) => (
                      <tr key={i} className="border-t border-gray-700">
                        <td className="p-2">{o.orderId || o.id || o.clientOrderId}</td>
                        <td className="p-2">{o.tradingSymbol || o.securityId || "-"}</td>
                        <td className="p-2">{o.transactionType || o.side || "-"}</td>
                        <td className="p-2">{o.quantity || o.qty || "-"}</td>
                        <td className="p-2">{o.orderStatus || o.status || "-"}</td>
                        <td className="p-2">
                          {(String(o.orderStatus || o.status || "").toUpperCase().includes("PENDING") ||
                            String(o.orderStatus || o.status || "").toUpperCase().includes("OPEN")) ? (
                            <button className="btn-danger" onClick={() => handleCancel(o.orderId || o.id)}>
                              Cancel
                            </button>
                          ) : (
                            <span className="text-gray-400 text-sm">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-gray-400 mt-2">No orders found</div>
            )}
          </div>
        </section>

        <footer className="text-center text-xs text-gray-500">
          Polling every 10s • Backend: {BASE_URL}
        </footer>
      </div>
    </div>
  );
}
