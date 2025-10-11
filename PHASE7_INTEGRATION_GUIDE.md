# Phase 7 Integration Guide

## 🔌 Quick Integration Instructions

The Phase 7 self-learning system is **95% complete**. All services are built and tested. 

Only **3 simple integration hooks** remain to connect learning to execution:

---

## ✅ What's Already Done

- ✅ 15 services created and working
- ✅ 8 API endpoints functional
- ✅ 6 database tables created
- ✅ Daily job scheduled (6 AM IST)
- ✅ Frontend components integrated
- ✅ Phase7Integrator service created (provides all hooks)

---

## ⏳ 3 Remaining Integration Hooks (30-45 minutes)

### **Hook 1: Record Trade Execution with Decision Linkage**

**File:** `backend-temp/modules/ai/services/executionEngine.js`  
**Method:** `executeOrder()` or wherever trades are recorded

**Add After Order Execution:**
```javascript
// After successful order placement (around line 315)
const getPhase7Integrator = require('./phase7Integrator');
const integrator = getPhase7Integrator();

// Link trade to AI decision for learning
await integrator.recordTradeExecution(
  result.trade_id,
  {
    symbol: order.symbol,
    entry_price: result.executed_price || order.price,
    quantity: order.quantity
  },
  automation.decision_id || null // If automation has decision_id from strategy creation
);
```

**Purpose:** Links trades to AI decisions for outcome analysis

---

### **Hook 2: Trigger Online Learning on Trade Close**

**File:** `backend-temp/modules/ai/services/executionEngine.js` or `paperTradingSimulator.js`  
**Method:** Wherever trades are marked as closed/complete

**Add When Trade Closes:**
```javascript
// When a trade reaches take profit, stop loss, or manual exit
if (trade.status === 'CLOSED' || trade.status === 'COMPLETE') {
  const getPhase7Integrator = require('./phase7Integrator');
  const integrator = getPhase7Integrator();
  
  // Trigger online learning
  await integrator.handleTradeClose(
    {
      id: trade.id,
      symbol: trade.symbol,
      decision_id: trade.decision_id,
      user_id: trade.user_id
    },
    {
      exit_price: trade.exit_price,
      pnl: trade.pnl,
      pnl_percent: trade.pnl_percent,
      exit_reason: trade.exit_reason || 'take_profit',
      user_override: trade.user_override || false,
      override_reason: trade.override_reason || null
    }
  );
}
```

**Purpose:** Real-time learning from outcomes, adjusts data source weights

---

### **Hook 3: Confidence Gatekeeper for Auto-Trades**

**File:** `backend-temp/modules/ai/services/executionEngine.js`  
**Method:** Before executing auto-trades (when tradingMode === 'auto')

**Add Before Auto-Execution:**
```javascript
// Before executing an auto-trade (check user's trading mode first)
if (automation.tradingMode === 'auto' || userTradingMode === 'auto') {
  const getPhase7Integrator = require('./phase7Integrator');
  const integrator = getPhase7Integrator();
  
  // Check if trade meets safety criteria
  const approval = await integrator.checkAutoTradeApproval(
    {
      confidence: automation.confidence || 0.7,
      decision_data: { selectedStocks: automation.selectedStocks },
      market_regime: automation.market_regime,
      decision_type: 'stock_selection'
    },
    automation.user_id
  );
  
  if (!approval.approved) {
    console.log(`[ExecutionEngine] Auto-trade blocked: ${approval.reason}`);
    
    // Move to pending_approval instead of auto-executing
    trade.status = 'pending_approval';
    trade.approval_reason = approval.reason;
    trade.gatekeeper_check = approval.check;
    
    // Notify user
    eventBus.emit('trade.requires_approval', {
      trade_id: trade.id,
      reason: approval.reason,
      recommendation: gatekeeper.getRecommendedAction(approval)
    });
    
    return { status: 'pending_approval', reason: approval.reason };
  }
  
  console.log('[ExecutionEngine] Gatekeeper approved auto-trade ✅');
  // Continue with execution
}
```

**Purpose:** Prevents low-confidence decisions from auto-executing

---

## 🎯 **Integration Steps (In Order)**

### **Step 1: Find Trade Execution Point**
```bash
cd backend-temp/modules/ai/services
grep -n "INSERT INTO strategy_trades" executionEngine.js
# Or look for where trade records are created
```

### **Step 2: Find Trade Close Point**
```bash
grep -n "take_profit\|stop_loss\|trade.*close" executionEngine.js paperTradingSimulator.js
# Or look for where positions are closed
```

### **Step 3: Find Auto-Trade Decision Point**
```bash
grep -n "tradingMode.*auto\|auto.*trading" executionEngine.js
# Or look for where auto vs manual is checked
```

### **Step 4: Add Hooks**
- Copy the code snippets above
- Paste at appropriate locations
- Test with a simple trade

---

## 🧪 **Testing After Integration**

### **Test Hook 1 (Execution Recording):**
```
1. Create a strategy via UI
2. Approve it
3. Let it execute a trade
4. Check database:
   SELECT * FROM trade_outcomes ORDER BY executed_at DESC LIMIT 1;
5. Should see entry_price, quantity recorded
```

### **Test Hook 2 (Trade Close Learning):**
```
1. Manually close a trade (or wait for take profit)
2. Check backend logs for:
   "[OnlineLearning] Processing trade close: RELIANCE, PnL: 250.50"
   "[OnlineLearning] Updated data source weights"
   "[OnlineLearning] Learning complete for trade 123"
3. Check database:
   SELECT * FROM trade_outcomes WHERE closed_at IS NOT NULL LIMIT 1;
4. Should see exit_price, pnl, pnl_percent filled
```

### **Test Hook 3 (Gatekeeper):**
```
1. Enable auto-trading mode
2. Create a strategy with:
   - Low confidence (<70%)
   - Or conflicting data sources
3. Expected: Trade goes to pending_approval, not auto-executed
4. Check logs for:
   "[ExecutionEngine] Auto-trade blocked: Low confidence (65% < 70%)"
5. High confidence (>70%) should auto-execute
```

---

## 🔍 **Where to Find Things**

### **Execution Engine:**
- File: `backend-temp/modules/ai/services/executionEngine.js`
- Likely methods: `executeOrder()`, `evaluateStrategy()`, `monitorStrategies()`

### **Paper Trading Simulator:**
- File: `backend-temp/modules/ai/services/paperTradingSimulator.js`
- Likely methods: `simulateOrder()`, `updatePosition()`

### **Strategy Automation Routes:**
- File: `backend-temp/modules/ai/routes/automation.js`
- Method: POST /strategy - Creates automation
- This is where decision_id should be stored in automation record

---

## 📊 **Database Schema Reference**

### **strategy_trades (Existing Table):**
Should have or can add:
```sql
ALTER TABLE strategy_trades ADD COLUMN IF NOT EXISTS decision_id INT REFERENCES ai_decisions(id);
```

### **strategy_automations (Existing Table):**
Should have or can add:
```sql
ALTER TABLE strategy_automations ADD COLUMN IF NOT EXISTS decision_id INT REFERENCES ai_decisions(id);
ALTER TABLE strategy_automations ADD COLUMN IF NOT EXISTS confidence FLOAT;
ALTER TABLE strategy_automations ADD COLUMN IF NOT EXISTS market_regime VARCHAR(50);
```

---

## 🎯 **Integration Priority**

### **Critical (Do First):**
1. **Hook 1** - Trade execution recording
   - Enables attribution tracking
   - Required for learning

2. **Hook 2** - Trade close learning
   - Triggers online learning
   - Updates data source weights
   - Core of self-learning

### **Important (Do Second):**
3. **Hook 3** - Confidence gatekeeper
   - Safety for auto-trading
   - Prevents bad decisions
   - User trust critical

### **Nice to Have (Optional):**
4. Explainability in API responses
5. Decision ID in automation records
6. Extended database columns

---

## 🚀 **Expected Behavior After Integration**

### **Scenario 1: First Strategy (No Learning Yet)**
```
User creates goal → AI selects stocks using research
Research: RELIANCE has positive news + 80% sentiment
Decision recorded with attribution: [news, sentiment]
Trade executes
Trade closes after 2 days: +5% profit
Online learning: "News and sentiment were ACCURATE"
Next decision: News and sentiment weight increased by 5%
```

### **Scenario 2: After 20 Trades**
```
Learning insights generated:
- "Fundamental data has 75% win rate - prioritize fundamentals"
- "Sentiment in BULL regime: 80% win rate"
- "News data mixed: 55% win rate - use with caution"

Next stock selection:
- LLM prompt includes these insights
- AI weights fundamentals higher than news
- Better stock selection due to learning
```

### **Scenario 3: Auto-Trade with Low Confidence**
```
AI Decision: BUY RELIANCE (confidence: 62%)
Gatekeeper: BLOCKED (62% < 70% threshold)
Trade → pending_approval
User reviews: Sees "Low confidence" reason
User can approve or reject
If approved: Executes, outcome tracked
If rejected: Recorded as user override for learning
```

---

## 🔧 **Troubleshooting**

### **If Learning Not Working:**
1. Check `trade_outcomes` table has records
2. Verify `decision_id` is not null in trades
3. Check backend logs for "[OnlineLearning]" messages
4. Run on-demand learning job to test

### **If Gatekeeper Always Approves:**
1. Check confidence values in decisions
2. Verify user performance has >10 trades
2. Lower threshold in `confidenceGatekeeper.js` for testing

### **If No Insights Generated:**
1. Need minimum 10 closed trades
2. Run: `POST /api/modules/ai/research/learning-job/run`
3. Check `learning_insights` table

---

## ✅ **Verification Checklist**

After integration:

- [ ] Trade execution creates record in `trade_outcomes`
- [ ] Trade close triggers online learning (check logs)
- [ ] Data source weights update after outcomes
- [ ] Confidence gatekeeper blocks low-confidence auto-trades
- [ ] Learning insights generated after 10+ trades
- [ ] Frontend displays regime and learnings
- [ ] Research panel shows attribution

---

## 📝 **Integration Complete When:**

1. Backend logs show: "[Phase7Integrator] ✅ Trade execution recorded"
2. Backend logs show: "[OnlineLearning] Learning complete for trade X"
3. Backend logs show: "[Phase7Integrator] Auto-trade blocked" (for low confidence)
4. Database `trade_outcomes` has records
5. Database `learning_insights` has rows after 10+ trades
6. Frontend Learning Insights Panel displays data

---

**Status:** Integration helpers ready, 3 hooks to add (~30-45 minutes)  
**When Complete:** Phase 7 fully operational, self-learning active  
**Next:** Collect 30 days of data, validate improvements
