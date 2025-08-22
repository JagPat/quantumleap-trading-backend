
# Automated Trading Dashboard Integration Guide

## 1. Add Route to App.jsx

```jsx
import AutomatedTradingPage from './pages/AutomatedTradingPage';

// Add to your routes
<Route path="/automated-trading" element={<AutomatedTradingPage />} />
```

## 2. Add Navigation to Sidebar

```jsx
import { TrendingUp } from '@mui/icons-material';

// Add to navigation items
{
  text: 'Automated Trading',
  icon: <TrendingUp />,
  path: '/automated-trading'
}
```

## 3. Install Required Dependencies

```bash
npm install react-chartjs-2 chart.js
```

## 4. Backend API Integration

The dashboard expects these API endpoints:
- GET /api/trading-engine/health
- GET /api/trading-engine/strategies
- GET /api/trading-engine/orders/active
- GET /api/trading-engine/positions
- GET /api/trading-engine/performance/current
- GET /api/trading-engine/risk/metrics
- GET /api/trading-engine/alerts/active
- POST /api/trading-engine/start
- POST /api/trading-engine/stop
- POST /api/trading-engine/emergency-stop

## 5. WebSocket Integration (Optional)

For real-time updates, implement WebSocket endpoint:
- WS /ws/trading-engine

## 6. Environment Variables

Add to .env:
```
REACT_APP_API_URL=http://localhost:8000
```

## 7. Features Included

### Main Dashboard
- Real-time trading status
- System health monitoring
- Performance charts
- Risk metrics visualization
- Active orders and positions
- Emergency controls

### Strategy Management
- Create/edit/delete strategies
- Enable/disable strategies
- Configure strategy parameters
- Monitor strategy performance

### Manual Overrides
- Create temporary overrides
- Block orders/symbols
- Modify risk limits
- Emergency stops

## 8. Mock Data

The service includes mock data methods for development:
- getMockStrategies()
- getMockActiveOrders()
- getMockPositions()
- getMockPerformanceData()
- getMockRiskMetrics()
- getMockSystemHealth()
- getMockAlerts()

## 9. Customization

### Adding New Strategy Types
Edit `getStrategyTypeOptions()` in StrategyManagement.jsx

### Adding New Override Types
Edit `getOverrideTypeOptions()` in ManualOverride.jsx

### Modifying Charts
Update chart configurations in AutomatedTradingDashboard.jsx

## 10. Testing

Run the test file to validate implementation:
```bash
python3 test_automated_trading_dashboard.py
```
