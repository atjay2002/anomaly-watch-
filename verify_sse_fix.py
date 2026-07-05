#!/usr/bin/env python3
"""
Quick test script to verify SSE fix.
Run this after restarting your Flask application.
"""

import sys

print("=" * 60)
print("SSE Fix Verification")
print("=" * 60)
print()

# Check if the fix is in place
try:
    with open('routes/stream.py', 'r') as f:
        content = f.read()

    # Check for the correct import
    if 'from services.sse_service import SSEEvent' in content:
        print("✓ Correct import statement found")
    else:
        print("✗ Import statement not found")
        sys.exit(1)

    # Check that we're not using sse_service.SSEEvent anymore
    if 'sse_service.SSEEvent' not in content:
        print("✓ No incorrect SSEEvent references found")
    else:
        print("✗ Still has incorrect references")
        sys.exit(1)

    # Check for correct usage
    if 'SSEEvent(' in content:
        print("✓ Correct SSEEvent usage found")
    else:
        print("✗ SSEEvent usage not found")
        sys.exit(1)

    print()
    print("=" * 60)
    print("✓ SSE Fix Applied Successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Restart your Flask application:")
    print("   sudo systemctl restart anomalywatch")
    print("   (or Ctrl+C and restart if running manually)")
    print()
    print("2. Refresh your browser dashboard")
    print()
    print("3. Check that the SSE connection stays active")
    print()

except FileNotFoundError:
    print("✗ routes/stream.py not found")
    print("  Make sure you're running this from the project root")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
