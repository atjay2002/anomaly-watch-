# SSE Connection Fix - Applied

## Problem
The SSE (Server-Sent Events) connection was failing with:
```
AttributeError: 'SSEService' object has no attribute 'SSEEvent'
```

## Root Cause
In `routes/stream.py`, the code was trying to access `SSEEvent` as an attribute of the `sse_service` instance:
```python
sse_service.SSEEvent(...)  # WRONG - SSEEvent is a class, not an instance attribute
```

## Solution Applied
Fixed by importing `SSEEvent` directly from the module:

**Before:**
```python
from services import sse_service
# ...
sse_service.SSEEvent(...)  # ERROR
```

**After:**
```python
from services import sse_service
from services.sse_service import SSEEvent  # Import the class directly
# ...
SSEEvent(...)  # CORRECT
```

## Files Modified
- `routes/stream.py` - Fixed import and all SSEEvent references

## How to Apply the Fix

### Option 1: If running as systemd service
```bash
sudo systemctl restart anomalywatch
```

### Option 2: If running manually
```bash
# Press Ctrl+C to stop the current process
# Then restart:
python app.py
```

### Option 3: Quick verification
```bash
python3 verify_sse_fix.py
```

## Testing the Fix

1. **Restart the application** (see above)

2. **Open the dashboard** at `http://localhost:5000`

3. **Check browser console** (F12 → Console tab):
   - Should see: `SSE connected: <client-id>`
   - Should NOT see: `Connection lost, reconnecting...`

4. **Verify live updates**:
   - Charts should update every ~5 seconds
   - System status should show "● System Healthy" (green)
   - Client count should show 1 or more

5. **Check server logs**:
   ```bash
   # If running as service:
   journalctl -u anomalywatch -f
   
   # Should see:
   # INFO - New SSE client connected: <uuid>
   # Should NOT see:
   # AttributeError: 'SSEService' object has no attribute 'SSEEvent'
   ```

## Expected Behavior After Fix

✅ SSE connection stays active indefinitely  
✅ Real-time charts update smoothly  
✅ No "Connection lost" messages  
✅ Heartbeat events every 30 seconds  
✅ Metric events every 5 seconds  

## Additional Notes

- The fix is backward compatible
- No database changes required
- No configuration changes needed
- Works with all existing features (alerts, baseline, testing)

## Troubleshooting

If you still see connection issues after applying the fix:

1. **Clear browser cache**: Ctrl+Shift+R (hard refresh)

2. **Check Flask is running**:
   ```bash
   curl http://localhost:5000/health
   ```

3. **Test SSE endpoint directly**:
   ```bash
   curl -N http://localhost:5000/stream/metrics
   # Should see: event: connected
   ```

4. **Check for port conflicts**:
   ```bash
   sudo lsof -i :5000
   ```

5. **Verify Python dependencies**:
   ```bash
   pip list | grep -E "(Flask|Werkzeug)"
   ```

## Status
✅ **Fix Applied and Verified** - Ready for use!
