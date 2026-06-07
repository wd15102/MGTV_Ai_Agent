"""Long-duration scrcpy stream test (30 frames, ~10 seconds)"""
import asyncio, sys, time
sys.path.insert(0, ".")
import logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from app.stream.scrcpy_reader import ScrcpyDeviceStreamReader


async def main():
    reader = ScrcpyDeviceStreamReader(
        adb_path=r"D:\Android\QtScrcpy-win-x64-v3.3.3\adb.exe",
        device_id="192.168.100.5:5555",
        scrcpy_server_path=r"D:\Android\QtScrcpy-win-x64-v3.3.3\scrcpy-server",
        max_size=720,
        bit_rate=2000000,
        decode_every_n=2,
    )

    ok = await reader.start()
    print(f"start() = {ok}")
    if not ok:
        return

    info = reader.stream_info
    print(f"stream: {info['codec']} {info['width']}x{info['height']}")

    t0 = time.time()
    frame_sizes = []
    for i in range(30):
        frame = await reader.get_frame(timeout=5)
        if frame:
            frame_sizes.append(len(frame))
        else:
            frame_sizes.append(0)
        elapsed = time.time() - t0
        sys.stdout.write(f"\r  frame {i+1:2d}/30: {frame_sizes[-1]:>5}B, elapsed={elapsed:.1f}s ")
        sys.stdout.flush()

    elapsed = time.time() - t0
    valid = [s for s in frame_sizes if s > 0]
    avg_size = sum(valid) / len(valid) if valid else 0
    fps = len(valid) / elapsed if elapsed > 0 else 0
    print(f"\n\nResults: {len(valid)}/30 frames in {elapsed:.1f}s")
    print(f"  Avg JPEG size: {avg_size:.0f} bytes")
    print(f"  Effective FPS: {fps:.1f}")
    print(f"  Frame sizes: min={min(valid) if valid else 0}, max={max(valid) if valid else 0}")

    await reader.stop()
    print("OK: stopped")


if __name__ == "__main__":
    asyncio.run(main())
