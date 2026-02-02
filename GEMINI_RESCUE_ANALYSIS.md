# Gemini 3 Pro Deep Analysis: Rescue System Optimization

Generated: Feb 2026

## Key Findings

### 1. Thinking Budget
- **8192 tokens is overkill** for 90% of rescue scenarios
- Most "stuck" states are tactical (modal blocking, dropdown needs click)
- **Recommended: Tier 1 = 0 thinking, Tier 2 = 4096 max**

### 2. WAF/Bot Detection
- "Something went wrong" on Indeed is usually **WAF block**, not logic error
- No amount of "Thinking" tokens will solve a network-level block
- **Solution: Detect and skip, don't waste tokens reasoning about it**

### 3. Tiered Rescue Architecture

```
Tier 1: Tactical Rescue (First attempt)
├── Model: Gemini 2.5 Flash
├── Thinking: DISABLED (0 tokens)
├── Use case: Popups, simple errors, button location
└── Cost: ~$0.001

Tier 2: Strategic Rescue (If Tier 1 fails)
├── Model: Gemini 3 Pro
├── Thinking: 4096 tokens
├── Use case: Complex logic, ambiguous errors
└── Cost: ~$0.01
```

### 4. Bot Detection Mitigations
- Residential proxies (already have)
- Bezier curve mouse movements (TODO)
- Viewport randomization (TODO)
- Idle scrolling before actions (TODO)

### 5. Efficiency
- Current: 30-50 steps per application
- Target: Use JS injection for form filling = ~10 steps
- Cache known error patterns instead of calling API

## Implementation Status

- [x] Tiered rescue (Flash → Pro)
- [x] WAF detection (skip on repeated "Something went wrong")
- [x] Thinking budget capped at 4096
- [ ] Bezier mouse movements
- [ ] JS form injection
- [ ] Error pattern caching
