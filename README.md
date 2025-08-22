# TradingView x Dhan Trading System

A robust, low-latency, production-ready system that receives TradingView alerts via webhooks and executes trades on Dhan using the official `dhanhq` library.

## 🚀 Features

- **TradingView Webhook Integration**: Receives real-time trading alerts
- **Dhan API Integration**: Uses official `dhanhq` library methods only
- **Idempotency**: Prevents duplicate trade execution using SHA256 hashing
- **Real-time Dashboard**: Monitor system status and test webhooks
- **Production Ready**: Comprehensive testing and CI/CD pipeline

## 🏗️ Architecture

```
TradingView → Webhook → FastAPI Backend → Dhan API → Trade Execution
                ↓
            SQLite Database (Alert Storage + Idempotency)
                ↓
            Frontend Dashboard (Status + Testing)
```

## 📋 Phase Structure

### Phase 0 — Project Setup & Structure ✅
- Clean repository with CI/CD
- Project scaffolding and dependencies
- Basic FastAPI application structure

### Phase 1 — FastAPI Skeleton & Health Endpoint ✅
- FastAPI application with health endpoints
- Basic API structure (`/healthz`, `/orders`)
- No business logic yet

### Phase 2 — Webhook Endpoint & Idempotency ✅
- TradingView webhook ingestion
- Pydantic validation schemas
- SHA256-based duplicate detection
- SQLite alert storage

### Phase 3 — Dhan API Integration (Coming Soon)
- Dynamic ATM options calculation
- Live exchange data integration
- Order placement using official methods

### Phase 4 — Trading Logic & Dashboard (Coming Soon)
- Manual test buttons (BUY CE / SELL CE)
- Real-time trade monitoring
- Performance analytics

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Trading**: Official `dhanhq` Python library
- **Testing**: pytest, pytest-asyncio
- **CI/CD**: GitHub Actions, Render deployment

## 📚 Dhan API Integration

This system uses **only** the official Dhan API methods as documented:

### Orders
- **Place Order**: `dhanhq.orders.place_order()`
- **Get Order Status**: `dhanhq.orders.get_order_status()`
- **Cancel Order**: `dhanhq.orders.cancel_order()`

### Square-off
- **Bracket Order**: `dhanhq.orders.place_bracket_order()` (if supported)
- **Manual Square-off**: Cancel existing orders and place reverse orders

### Rate Limits
- **Order Rate**: 25 orders/second (per Dhan documentation)
- **API Limits**: As per official Dhan API specifications

### Important Notes
- ❌ **NO custom HTTP endpoints**
- ❌ **NO manual order building**
- ❌ **NO unauthorized API calls**
- ✅ **ONLY documented dhanhq methods**
- ✅ **ONLY official library functions**

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git
- Dhan trading account

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Smeet1350/Trading-view-x-Dhan.git
   cd Trading-view-x-Dhan
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   export WEBHOOK_TOKEN="your_webhook_token"
   export ALERT_DB_PATH="alerts.db"
   ```

4. **Run the backend**
   ```bash
   python -m uvicorn backend.app.main:app --reload
   ```

5. **Open frontend**
   - Navigate to `frontend/index.html` in your browser
   - Or serve with a local web server

### Testing

Run all tests:
```bash
pytest backend/tests/ -v
```

Run specific phase tests:
```bash
pytest backend/tests/phase_00/ -v  # Phase 0
pytest backend/tests/phase_01/ -v  # Phase 1
pytest backend/tests/phase_02/ -v  # Phase 2
```

## 🌐 API Endpoints

### Health & Status
- `GET /` - System information and features
- `GET /healthz` - Health check endpoint
- `GET /orders` - Get orders (placeholder)

### Webhook
- `POST /webhook` - TradingView webhook endpoint
- `GET /webhook/status` - Webhook status and alert count

### Authentication
- **Header**: `X-WEBHOOK-TOKEN`
- **Environment Variable**: `WEBHOOK_TOKEN`

## 📊 Webhook Payload Format

```json
{
  "id": "unique-alert-id",
  "symbol": "NIFTY" | "BANKNIFTY",
  "signal": "BUY CE" | "SELL CE" | "BUY PE" | "SELL PE",
  "ts": "2024-12-26T10:00:00"
}
```

## 🔒 Security Features

- **Webhook Authentication**: Token-based authentication
- **Input Validation**: Pydantic schema validation
- **Idempotency**: SHA256 hash-based duplicate detection
- **SQL Injection Protection**: Parameterized queries
- **Environment Variables**: Sensitive data isolation

## 🧪 Testing Strategy

- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **Phase Tests**: Sequential feature validation
- **CI/CD**: Automated testing on every commit
- **Manual Testing**: Frontend dashboard testing

## 📈 Deployment

### Local Development
- FastAPI with auto-reload
- SQLite database
- Frontend served locally

### Production (Render)
- Automatic deployment from GitHub
- Environment variable management
- Health check monitoring
- Auto-scaling capabilities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This system is for educational and development purposes. Trading involves substantial risk of loss and is not suitable for all investors. Always test thoroughly in a paper trading environment before using real money.

## 🔗 Links

- **Repository**: https://github.com/Smeet1350/Trading-view-x-Dhan
- **Dhan API Documentation**: [Official Dhan API Docs](https://dhan.co/api-docs)
- **TradingView**: [TradingView Webhooks](https://www.tradingview.com/support/solutions/43000516366-webhooks/)
- **FastAPI**: [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 📞 Support

For issues and questions:
- Create an issue in this repository
- Check the documentation
- Review the test files for examples

---

**Built with ❤️ for the trading community**
