# 🚨 Rate Limiting Fix for Debate Arena

## Problem
Groq API has rate limits (free tier: ~30 requests/minute). Debate Arena makes 6+ LLM calls per debate (2 per round × 3 rounds), causing 429 errors.

## Solution Implemented ✅

### 1. **Rate Limiting with Sleep**
```python
# In DebateArenaAgent.__init__
self.last_request_time = 0
self.min_request_interval = 2.0  # 2 seconds between requests
```

### 2. **Exponential Backoff Retry**
```python
def _rate_limited_llm_call(self, messages: list, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            # Wait if needed
            time_since_last = time.time() - self.last_request_time
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)

            # Make call
            response = self.groq_client.chat.completions.create(...)
            return response

        except Exception as e:
            if "429" in str(e):
                # Exponential backoff: 3s, 6s, 12s
                wait_time = (2 ** attempt) * 3
                time.sleep(wait_time)
```

### 3. **Reduced Rounds**
- **Before**: 5 rounds (10 LLM calls)
- **After**: 3 rounds (6 LLM calls)
- **Time**: ~18-20 seconds per debate (with rate limiting)

## Expected Behavior Now

### Timing
```
Round 1 Team A: 2s wait + call
Round 1 Team B: 2s wait + call
Round 2 Team A: 2s wait + call
Round 2 Team B: 2s wait + call
Round 3 Team A: 2s wait + call
Round 3 Team B: 2s wait + call
Total: ~18-20 seconds
```

### If Rate Limited
```
Attempt 1: Failed (429)
Wait: 3 seconds
Attempt 2: Failed (429)
Wait: 6 seconds
Attempt 3: Success
```

## Alternative Solutions (if still hitting limits)

### Option A: Use Smaller Model
```python
# In main.py
debate_agent = DebateArenaAgent(
    groq_model="llama-3.1-8b-instant"  # Faster, higher rate limit
)
```

### Option B: Increase Wait Time
```python
# In debate_arena.py
self.min_request_interval = 3.0  # 3 seconds instead of 2
```

### Option C: Batch Mode (Future)
Generate all arguments in parallel, then wait once:
```python
# Pseudo-code
args = await asyncio.gather(
    generate_arg_team_a(),
    generate_arg_team_b()
)
await asyncio.sleep(2)  # Single wait
```

### Option D: Upgrade Groq Plan
- Free: 30 req/min
- Paid: 300+ req/min
- Cost: ~$0.50/debate

## Monitoring

Check logs for:
```
Rate limit hit, waiting 3s (attempt 1/3)
Rate limit hit, waiting 6s (attempt 2/3)
```

If you see this frequently, increase `min_request_interval`.

## Testing

```bash
# Run debate
# Watch terminal for:
# ✅ No "429 Too Many Requests"
# ✅ Smooth 2-second intervals between calls
# ✅ Debate completes in ~20 seconds
```

## Files Modified

- `backend/apps/api/src/agents/debate_arena.py`
  - Added `_rate_limited_llm_call()` method
  - Added retry logic with exponential backoff
  - Reduced default rounds to 3

- `frontend/apps/web/lib/api.ts`
  - Updated default rounds to 3

- `frontend/apps/web/components/debate/debate-arena.tsx`
  - Updated UI to show "3 Rounds"

## Current Settings

| Setting | Value | Reason |
|---------|-------|--------|
| Rounds | 3 | Reduce API calls |
| Min interval | 2.0s | Stay under rate limit |
| Max retries | 3 | Handle transient errors |
| Backoff | Exponential (3s, 6s, 12s) | Progressive waiting |

## If You Want 5 Rounds Back

**After getting Groq paid plan:**

1. Update `debate_arena.py`:
   ```python
   rounds: int = 5  # Back to 5!
   ```

2. Update `api.ts`:
   ```python
   rounds: number = 5
   ```

3. Update UI:
   ```tsx
   <div>5 Rounds</div>
   ```

4. Consider reducing interval:
   ```python
   self.min_request_interval = 1.0  # Faster with paid plan
   ```

---

**Status**: ✅ Fixed! Debate should work smoothly now with 3 rounds and rate limiting.
