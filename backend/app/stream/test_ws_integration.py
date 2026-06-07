"""End-to-end WebSocket screen stream integration test"""
import asyncio, json, urllib.request, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from websockets.asyncio.client import connect
except ImportError:
    from websockets import connect


async def test():
    await asyncio.sleep(1)

    url = "http://127.0.0.1:8090"
    
    # Test REST API
    try:
        r = urllib.request.urlopen(f"{url}/api/status")
        data = json.loads(r.read())
        print(f"REST API: {data['status']} v{data['version']}")
    except Exception as e:
        print(f"API fail: {e}")
        return

    # Test WebSocket screen stream
    ws_url = f"ws://127.0.0.1:8090/ws/device/192.168.100.5:5555/screen"
    try:
        async with connect(ws_url) as ws:
            print(f"WS connected to {ws_url}")

            got_frames = 0
            for i in range(8):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    if isinstance(msg, bytes):
                        got_frames += 1
                        size_kb = len(msg) / 1024
                        print(f"  frame #{got_frames}: {size_kb:.1f} KB")
                    else:
                        print(f"  msg #{i+1}: {msg[:100]}")
                except asyncio.TimeoutError:
                    print(f"  attempt #{i+1}: TIMEOUT (no new data)")
            
            if got_frames > 0:
                print(f"\nSUCCESS: {got_frames} frames received via WebSocket!")
            else:
                print(f"\nFAIL: No frames received")
    except Exception as e:
        print(f"WS error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
