# Job Bot - Development TODO

Track progress here. Check off items as completed.

---

## Phase 1: Form Injection (HIGH IMPACT)
*Goal: Reduce 40 steps → 3-5 steps*

- [ ] **1.1** Create `skills/form_filler.js` - React-aware injection script
- [ ] **1.2** Create `skills/dom_parser.py` - HTML cleaner for LLM input
- [ ] **1.3** Add `inject_form` action to controller
- [ ] **1.4** Add heuristic field matching (regex for name/email/phone)
- [ ] **1.5** Test on Indeed Easy Apply form
- [ ] **1.6** Test on Greenhouse form

---

## Phase 2: Pattern Cache (COST REDUCTION)
*Goal: Skip LLM for known forms*

- [ ] **2.1** Create `memory/pattern_store.py` - CRUD for patterns
- [ ] **2.2** Implement `calculate_form_signature()`
- [ ] **2.3** Create `patterns.json` initial structure
- [ ] **2.4** Add cache lookup before LLM calls
- [ ] **2.5** Add success/failure tracking
- [ ] **2.6** Manually seed Greenhouse/Lever patterns

---

## Phase 3: Multi-Tier Orchestrator
*Goal: Smart tier escalation*

- [ ] **3.1** Refactor main loop into state machine
- [ ] **3.2** Implement tier selection logic
- [ ] **3.3** Add Tier 0 (cache) integration
- [ ] **3.4** Add Tier 1 (heuristics) integration
- [ ] **3.5** Test full escalation flow

---

## Phase 4: Humanization
*Goal: Avoid bot detection*

- [ ] **4.1** Implement Bezier mouse movement
- [ ] **4.2** Add Gaussian timing delays
- [ ] **4.3** Add idle scroll behaviors
- [ ] **4.4** Add viewport randomization
- [ ] **4.5** Test against Indeed bot detection

---

## Phase 5: External ATS Handlers
*Goal: Handle Greenhouse, Lever, etc.*

- [ ] **5.1** Create `handlers/greenhouse.py`
- [ ] **5.2** Create `handlers/lever.py`
- [ ] **5.3** Test with real job postings
- [ ] **5.4** Add to pattern cache

---

## Phase 6: LinkedIn (RESEARCH FIRST)
*Goal: LinkedIn Easy Apply*

- [ ] **6.1** Research LinkedIn bot detection
- [ ] **6.2** Test session persistence
- [ ] **6.3** Create `handlers/linkedin.py`
- [ ] **6.4** Handle rate limiting

---

## Phase 7: Self-Improvement
*Goal: Learn from applications*

- [ ] **7.1** Implement session recording
- [ ] **7.2** Add feedback processing
- [ ] **7.3** Auto-promote successful patterns
- [ ] **7.4** Build metrics dashboard

---

## Quick Commands

```bash
# Run 5 applications
python3 bot/applier.py --max 5

# Check queue status
cat queue/pending.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Pending: {len(d)}')"

# View recent logs
tail -100 /tmp/applier_test.log
```

## Notes
- Use Gemini for heavy analysis (tokens cheap)
- Save Claude context for code changes
- Commit after each phase completion
