# TradingView x Dhan Trading System

A robust, low-latency, production-ready system that receives TradingView alerts via webhook and automatically places options orders on Dhan using the official dhanhq library.

## System Overview

This system provides:
- **Webhook Integration**: Receives TradingView alerts and processes them asynchronously
- **Dynamic ATM Calculation**: Computes current ATM options contract (strike & expiry) using live market data
- **Dhan Integration**: Places orders using only official dhanhq library methods
- **Dashboard UI**: Simple monitoring interface with manual test buttons
- **Production Ready**: Deployed on Render with comprehensive testing and CI/CD

## Architecture

```
TradingView Alert → Webhook → ATM Calculation → Dhan Order → Dashboard
     ↓              ↓           ↓              ↓           ↓
  JSON Payload  Validation  Market Data   Official    Real-time
  (BUY/SELL)   + Auth      + Expiry      DhanHQ      Monitoring
```

## Dhan API Integration

This system uses **ONLY** the official dhanhq library methods as documented:

### Orders
- **Place Order**: `dhanhq.orders.place_order()` - Places new options orders
- **Order Status**: `dhanhq.orders.get_order_status()` - Retrieves order status and fills
- **Bracket Orders**: `dhanhq.orders.place_bracket_order()` - For automated square-off (if supported)

### Rate Limits
- Per Dhan's documentation: 25 orders/second
- Implemented with asyncio.Semaphore for concurrency control

### Documentation References
- [Dhan API Documentation](https://dhanhq.co/docs/v2/orders/)
- [Orders API Reference](https://dhanhq.co/docs/v2/orders/place-order)
- [Order Status API](https://dhanhq.co/docs/v2/orders/get-order-status)

## Project Structure

```
backend/
  app/
    main.py              # FastAPI application entry point
    api/                 # API route handlers
    services/            # Business logic services
    models/              # Pydantic data models
  tests/                 # Test suite
frontend/
  index.html            # Dashboard HTML
  app.js               # Dashboard JavaScript
  styles.css           # Dashboard styles
requirements.txt        # Python dependencies
render.yaml            # Render deployment configuration
README.md              # This file
```

## Development Phases

This project follows a strict 10-phase development approach:

1. **Phase 0**: Project Setup & Structure ✅
2. **Phase 1**: FastAPI Skeleton & Health Endpoint
3. **Phase 2**: Webhook Endpoint & Idempotency
4. **Phase 3**: Market Data & Dynamic ATM + Expiry Logic
5. **Phase 4**: DhanHQ Library Integration (Official Methods Only)
6. **Phase 5**: Orchestrating Alert → ATM → Order Path
7. **Phase 6**: Dashboard & Event Streaming
8. **Phase 7**: Manual Test Buttons (BUY CE / SELL CE)
9. **Phase 8**: GitHub CI & Commit Discipline
10. **Phase 9**: Deployment to Render
11. **Phase 10**: Documentation, Runbook, and Final Release

## Safety Features

- **DRY_RUN Mode**: All orders are simulated when enabled
- **Token Authentication**: Webhook and admin access require valid tokens
- **Idempotency**: Duplicate alerts are detected and rejected
- **Rate Limiting**: Respects Dhan's documented rate limits
- **Error Handling**: Comprehensive error handling and logging

## Latency Considerations

**Important**: This system is designed for optimized millisecond latency, not microsecond performance. True microsecond latency is not achievable via public HTTP endpoints due to:

- Network latency (typically 10-100ms)
- HTTP overhead
- Internet routing delays
- Dhan API response times

The system aims to minimize latency through:
- Async processing
- Efficient market data caching
- Optimized order placement pipeline
- Background processing for non-critical operations

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables (see `.env.example`)
4. Run tests: `pytest`
5. Start development server: `uvicorn backend.app.main:app --reload`

## Environment Variables

```bash
WEBHOOK_TOKEN=your_webhook_secret
ADMIN_TOKEN=your_admin_secret
DHAN_TOKEN=your_dhan_api_token
DRY_RUN=true  # Set to false for production
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific phase tests
pytest tests/phase_01/
```

## Contributing

- All changes must pass CI/CD pipeline
- Follow the phased development approach
- Maintain 85%+ test coverage
- Use only official DhanHQ library methods
- No custom HTTP calls to Dhan endpoints

## License

MIT License - see LICENSE file for details.
