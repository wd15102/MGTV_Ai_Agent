"""Quick test for ScrcpyDeviceStreamReader"""
import asyncio, sys
sys.path.insert(0, ".")

from app.stream.scrcpy_reader import ScrcpyDeviceStreamReader


async def main():
    reader = ScrcpyDeviceStreamReader(
        adb_path=r"D:\Android\QtScrcpy-win-x64-v3.3.3\adb.exe",
        device_id="192.168.100.5:5555",
        scrcpy_server_path=r"D:\Android\QtScrcpy-win-x64-v3.3.3\scrcpy-server",
        max_size=720,
        bit_rate=2000000,
    )

    ok = await reader.start()
    print(f"start() = {ok}")
    if not ok:
        return

    info = reader.stream_info
    w, h = info["width"], info["height"]
    print(f"stream: {info['codec']} {w}x{h}, device='{info['device_name']}'")

    for i in range(5):
        frame = await reader.get_frame(timeout=10)
        if frame:
            print(f"  frame {i+1}: {len(frame)} B JPEG ({w}x{h})")
        else:
            print(f"  frame {i+1}: TIMEOUT")

    await reader.stop()
    print("OK: stopped")


if __name__ == "__main__":
    asyncio.run(main())
