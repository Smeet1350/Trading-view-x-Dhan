// App.jsx
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";

// Back-end must run here:
const BASE_URL =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_URL)
    ? import.meta.env.VITE_API_URL
    : (window.location.port === "5173"     // Vite dev server
        ? "http://localhost:8000"          // talk to local FastAPI
        : window.location.origin);          // same-origin in prod/Render

function safeMsg(x) {
  if (!x && x !== 0) return "";
  if (typeof x === "string") return x;
  if (typeof x === "object") {
    try { return JSON.stringify(x); } catch { return String(x); }
  }
  return String(x);
}

export default function App() {
  const [status, setStatus] = useState("Checking...");
  const [statusError, setStatusError] = useState(null);
  const [notif, setNotif] = useState(null);

  const [funds, setFunds] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);

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

  const [error, setError] = useState(null);
  const [placing, setPlacing] = useState(false);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [marketNotice, setMarketNotice] = useState("");
  const [exitModal, setExitModal] = useState(null); 
  // null or {symbol, segment, securityId, qty, side}

  const [liveAlerts, setLiveAlerts] = useState([]);      // ephemeral 20s cards
  const seenAlertIdsRef = useRef(new Set());            // dedup across polls
  const alertsPollRef = useRef(null);
  const alertsCleanRef = useRef(null);

  const pollRef = useRef(null);
  const searchDebounceRef = useRef(null);

  const api = axios.create({ baseURL: BASE_URL, timeout: 30000 }); // 30s instead of 15s
  const log = (...args) => console.log("[UI]", ...args);
  const toast = (m) => { setNotif(m); setTimeout(() => setNotif(null), 4000); };

  const fetchAll = async () => {
    try {
      const s = await api.get("/status");
      if (s.data?.status === "ok" || s.data?.status === "degraded") {
        const okDB = s.data?.instruments_db_current_today;
        const okBroker = s.data?.broker_ready;
        setStatus(`Connected ${okBroker ? "✅" : "⚠️"} ${okDB ? "" : "(Instrument DB outdated)"}`);
        setStatusError(s.data?.message || null);
      } else {
        setStatus("Not Connected ❌");
        setStatusError(s.data?.message || "Backend not reachable at " + BASE_URL);
      }

      const f = await api.get("/funds");
      setFunds(f.data?.data ?? null);

      const h = await api.get("/holdings");
      setHoldings(h.data?.data ?? []);

      const p = await api.get("/positions");
      setPositions(p.data?.data ?? []);
    } catch (err) {
      const msg = "Backend unreachable: " + safeMsg(err.message || err);
      setStatus("Not Connected ❌");
      setStatusError(msg);
      setError(msg);
      toast("💥 " + msg);
    }
  };

  useEffect(() => {
    fetchAll();
    pollRef.current = setInterval(fetchAll, 10000);
    return () => clearInterval(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchOrders = async () => {
    setLoadingOrders(true);
    try {
      const r = await api.get("/orders");
      setOrders(r.data?.data ?? []);
    } catch (e) {
      const msg = "Error fetching orders: " + safeMsg(e.message || e);
      setOrders([]);
      setError(msg);
      toast("💥 " + msg);
    } finally {
      setLoadingOrders(false);
    }
  };
  useEffect(() => {
    fetchOrders();
    const id = setInterval(fetchOrders, 10000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(async () => {
      try {
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

  // Alerts polling and expiry effect
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const r = await api.get("/webhook/alerts", { params: { limit: 100 } });
        const arr = r.data?.alerts || [];
        const now = Date.now();

        // Collect only *new* alerts we haven't seen (dedup by stable backend id)
        const newOnes = [];
        for (const a of arr) {
          const id = a?.id;
          if (!id) continue;
          if (!seenAlertIdsRef.current.has(id)) {
            seenAlertIdsRef.current.add(id);

            // Console log to the WEBSITE devtools (your Ctrl+Shift+I console)
            // Use groups for readability
            try {
              const label = `[ALERT ${String(a?.response?.status || "unknown").toUpperCase()}] ${a?.request?.index || "-"} ${a?.request?.strike || "-"}${a?.request?.option_type || ""} ${a?.request?.side || ""} @ ${a?.timestamp || "-"}`;
              console.groupCollapsed(label);
              console.log("Request:", a?.request);
              console.log("Instrument:", a?.instrument);
              console.log("Response:", a?.response);
              console.groupEnd();
            } catch { /* ignore console errors */ }

            // Enrich with local expiry for the dashboard (20s)
            newOnes.push({ ...a, _expiry: now + 20000 });
          }
        }

        if (newOnes.length) {
          // Merge with existing (keep not expired), and prepend new ones
          setLiveAlerts(prev => {
            const survived = prev.filter(x => Date.now() < x._expiry);
            return [...newOnes, ...survived];
          });
        }
      } catch {
        // ignore fetch errors for alerts
      }
    };

    // first tick + poll every 5s
    fetchAlerts();
    alertsPollRef.current = setInterval(fetchAlerts, 5000);

    // sweeper every 1s to enforce the 20s expiry *reliably*
    alertsCleanRef.current = setInterval(() => {
      setLiveAlerts(prev => prev.filter(x => Date.now() < x._expiry));
    }, 1000);

    return () => {
      if (alertsPollRef.current) clearInterval(alertsPollRef.current);
      if (alertsCleanRef.current) clearInterval(alertsCleanRef.current);
    };
  }, []);

  const pickInstrument = (inst) => {
    setSelectedInstrument({ ...inst, security_id: String(inst.securityId) });
    setSearchQuery(inst.tradingSymbol + (inst.expiry ? ` ${inst.expiry}` : ""));
    setSearchResults([]);
  };

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
      let securityId = selectedInstrument?.securityId ?? selectedInstrument?.security_id;
      if (!securityId) {
        try {
          const r = await api.get(`${BASE_URL}/resolve-symbol`, {
            params: { symbol: selectedInstrument.tradingSymbol, segment: selectedInstrument.segment }
          });
          if (r.data && r.data.inst) {
            securityId = String(r.data.inst.securityId);
            setSelectedInstrument(prev => ({ ...prev, security_id: securityId }));
          } else {
            throw new Error(r.data?.message || "Could not resolve symbol");
          }
        } catch (e) {
          const msg = `❌ Resolve failed: ${safeMsg(e)}`;
          setError(msg);
          toast(msg);
          setPlacing(false);
          return;
        }
      }

      const params = {
        symbol: selectedInstrument.tradingSymbol,
        security_id: securityId,
        segment,
        side,
        qty: Number(qty),
        order_type: orderType,
        price: Number(price) || 0,
        product_type: productType,
        validity,
      };
      const res = await api.post("/order/place", null, { params });
      if (res.data.status === "success") {
        toast("✅ Order placed successfully!");
        setMarketNotice(res.data?.message || "");
        await fetchOrders();
        await fetchAll();
      } else {
        const msg = `❌ Order failed [rid ${res.data.rid}]: ${safeMsg(res.data.message)}`;
        setError(msg);
        toast("💥 " + msg);
      }
    } catch (e1) {
      // If backend actually responded with a payload, show that
      if (e1.response && e1.response.data) {
        const msg = `❌ Order failed [rid ${e1.response.data.rid || "-"}]: ${safeMsg(e1.response.data.message)}`;
        setError(msg);
        toast("💥 " + msg);
      } else {
        const msg = "Network/timeout error while placing order — check backend logs";
        setError(msg);
        toast("💥 " + msg);
      }
    } finally {
      setPlacing(false);
    }
  };

  const handleCancel = async (orderId) => {
    if (!orderId) return;
    if (!window.confirm(`Cancel order ${orderId}?`)) return;
    try {
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
            <div className="overflow-auto max-h-96 mt-2">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>Available: ₹{money(funds.availabelBalance ?? funds.available ?? funds.avail ?? funds.availableBalance)}</div>
                <div>Withdrawable: ₹{money(funds.withdrawableBalance ?? funds.withdrawable ?? funds.withdraw)}</div>
                <div>SOD Limit: ₹{money(funds.sodLimit ?? funds.sodLimit)}</div>
                <div>Collateral: ₹{money(funds.collateralAmount ?? funds.collateral)}</div>
              </div>
            </div>
          ) : (
            <div className="text-gray-400 text-sm mt-2">Funds not available</div>
          )}
        </section>

        {/* Holdings */}
        <section className="card">
          <h2 className="font-semibold text-lg text-yellow-300">📦 Holdings</h2>
          {holdings.length > 0 ? (
            <div className="overflow-auto max-h-96 mt-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-300">
                    <th className="p-2">Symbol</th>
                    <th className="p-2">Qty</th>
                    <th className="p-2">Avg</th>
                    <th className="p-2">LTP</th>
                    <th className="p-2">P&L</th>
                    <th className="p-2">Action</th>
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
                        <td className="p-2">
                          <button className="btn-danger" onClick={() => setExitModal({
                            source: "holding",
                            symbol: h.tradingSymbol,
                            segment: h.segment || "NSE_EQ",
                            securityId: h.securityId,
                            qty: qtyv,
                            side: "SELL", // always sell holdings
                          })}>
                            Exit
                          </button>
                        </td>
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
            <div className="overflow-auto max-h-96 mt-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-300">
                    <th className="p-2">Symbol</th>
                    <th className="p-2">Qty</th>
                    <th className="p-2">Avg</th>
                    <th className="p-2">LTP</th>
                    <th className="p-2">P&L</th>
                    <th className="p-2">Action</th>
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
                        <td className="p-2">
                          <button className="btn-danger" onClick={() => setExitModal({
                            source: "position",
                            symbol: p.tradingSymbol,
                            segment: p.segment || "NSE_EQ",
                            securityId: p.securityId,
                            qty: Math.abs(qtyv),
                            side: qtyv > 0 ? "SELL" : "BUY", // opposite to close
                          })}>
                            Exit
                          </button>
                        </td>
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

            <div className="md:col-span-2 relative">
              <label className="block text-xs text-gray-400">Symbol / Search</label>
              <div className="relative">
                <input
                  type="text"
                  className="input pr-8"
                  placeholder="Type symbol (e.g. TCS or NIFTY24SEP...)"
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setSelectedInstrument(null); }}
                />
                {searchQuery && (
                  <button
                    type="button"
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                    onClick={() => { setSearchQuery(""); setSelectedInstrument(null); setSearchResults([]); }}
                  >
                    ✕
                  </button>
                )}
              </div>

              {searchResults.length > 0 && (
                <ul className="bg-gray-800 mt-1 rounded max-h-44 overflow-auto border border-gray-700">
                  <div className="bg-gray-900 text-xs px-2 py-1 text-gray-400 border-b border-gray-700">
                    Showing results in {segment}
                  </div>
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
              {searchQuery && searchResults.length === 0 && (
                <div className="text-xs opacity-70 mt-1">
                  No results. Check Instruments status or try exact symbol.
                </div>
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
              <button type="submit" className="bg-green-600 px-4 py-2 rounded hover:bg-green-700"
                disabled={placing || !(selectedInstrument?.securityId || selectedInstrument?.security_id)}>
                {placing ? "Placing..." : "Place Order"}
              </button>

              <div className="ml-auto text-sm text-gray-400">
                {selectedInstrument ? (
                  <div>
                    <div><strong>Selected:</strong> {selectedInstrument.tradingSymbol} (ID: {selectedInstrument.securityId || selectedInstrument.security_id})</div>
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

          <div>
            <h3 className="font-semibold">Order Book</h3>
            {loadingOrders ? (
              <div className="text-sm text-gray-400 mt-2">Loading orders...</div>
            ) : orders && orders.length > 0 ? (
              <div className="overflow-auto max-h-96 mt-2">
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

        {/* Live Webhook Alerts (auto vanish after 20s) */}
        <section className="card">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg text-pink-300">⚡ Live Webhook Alerts (20s)</h2>
            <div className="text-xs text-gray-400">showing {liveAlerts.length}</div>
          </div>

          {liveAlerts.length === 0 ? (
            <div className="text-sm text-gray-400 mt-2">No recent alerts</div>
          ) : (
            <div className="space-y-2 mt-3">
              {liveAlerts.map(a => (
                <div
                  key={a.id}
                  className={`p-3 rounded-lg ${String(a?.response?.status).toLowerCase()==="success" ? "bg-green-800/60" : "bg-red-800/60"}`}
                >
                  <div className="text-xs text-gray-300">
                    {a.timestamp}
                  </div>
                  <div className="font-medium">
                    {a?.request?.index} {a?.request?.strike}{a?.request?.option_type} {a?.request?.side}
                    {a?.request?.lots ? ` • ${a.request.lots} lot(s)` : ""}
                  </div>
                  <div className="text-xs">
                    <span className="opacity-70">Status:</span> {a?.response?.status || "-"} • <span className="opacity-70">Msg:</span> {a?.response?.message || "-"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <footer className="text-center text-xs text-gray-500">
          Polling every 10s • Backend: {BASE_URL}
        </footer>
      </div>

      {exitModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-xl shadow-xl w-full max-w-md">
            <h3 className="text-lg font-semibold mb-3">Square Off: {exitModal.symbol}</h3>

            <div className="space-y-2">
              <div>
                <label className="block text-xs text-gray-400">Quantity</label>
                <input type="number" className="input"
                  value={exitModal.qty}
                  onChange={(e)=>setExitModal({...exitModal, qty: Number(e.target.value)})}/>
              </div>

              <div>
                <label className="block text-xs text-gray-400">Order Type</label>
                <select className="select"
                  value={exitModal.orderType || "MARKET"}
                  onChange={(e)=>setExitModal({...exitModal, orderType: e.target.value})}>
                  <option value="MARKET">MARKET</option>
                  <option value="LIMIT">LIMIT</option>
                </select>
              </div>

              {exitModal.orderType === "LIMIT" && (
                <div>
                  <label className="block text-xs text-gray-400">Price</label>
                  <input type="number" step="0.01" className="input"
                    value={exitModal.price || ""}
                    onChange={(e)=>setExitModal({...exitModal, price: e.target.value})}/>
                </div>
              )}

              <div>
                <label className="block text-xs text-gray-400">Product</label>
                <select className="select"
                  value={exitModal.productType || "INTRADAY"}
                  onChange={(e)=>setExitModal({...exitModal, productType: e.target.value})}>
                  <option value="DELIVERY">DELIVERY/CNC</option>
                  <option value="INTRADAY">INTRADAY/MIS</option>
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-400">Validity</label>
                <select className="select"
                  value={exitModal.validity || "DAY"}
                  onChange={(e)=>setExitModal({...exitModal, validity: e.target.value})}>
                  <option value="DAY">DAY</option>
                  <option value="IOC">IOC</option>
                </select>
              </div>
            </div>

            <div className="flex gap-2 justify-end mt-4">
              <button className="btn" onClick={()=>setExitModal(null)}>Cancel</button>
              <button className="btn-danger"
                onClick={async ()=>{
                  try {
                    const params = {
                      symbol: exitModal.symbol,
                      segment: exitModal.segment,
                      side: exitModal.side,
                      qty: exitModal.qty,
                      order_type: exitModal.orderType || "MARKET",
                      price: Number(exitModal.price) || 0,
                      product_type: exitModal.productType || "INTRADAY",
                      validity: exitModal.validity || "DAY",
                      security_id: exitModal.securityId,
                    };
                    const res = await api.post("/order/place", null, { params });
                    if (res.data.status === "success") {
                      toast("✅ Square off order placed!");
                      fetchAll();
                      fetchOrders();
                      setExitModal(null);
                    } else {
                      toast("❌ " + safeMsg(res.data.message));
                    }
                  } catch (err) {
                    toast("💥 Error: " + safeMsg(err.message || err));
                  }
                }}>
                Confirm Exit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
