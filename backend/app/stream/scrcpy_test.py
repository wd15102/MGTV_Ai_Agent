"""
Scrcpy H.264 stream with proper protocol parsing
Protocol (QtScrcpy fork): 
  65B header [1B dummy + 64B device_name]
  12B stream meta [4B codec_name + 4B width + 4B height]
  Repeated: 12B frame_meta [8B PTS/flags + 4B pkt_size] + [pkt_size B data]
"""
import socket, subprocess, time, os, cv2, tempfile
import numpy as np

ADB = r"D:\Android\QtScrcpy-win-x64-v3.3.3\adb.exe"
DEVICE = "192.168.100.5:5555"
JAR = "/data/local/tmp/scrcpy-server"
PORT = 27193

def recvall(sock, n):
    """Read exactly n bytes from socket, returns None on timeout/disconnect"""
    data = b''
    while len(data) < n:
        try:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        except socket.timeout:
            return None
    return data

def main():
    print("=== Scrcpy H.264 Stream Protocol ===\n")
    
    # Clean + setup forward
    subprocess.run([ADB, '-s', DEVICE, 'forward', '--remove', f'tcp:{PORT}'],
                   capture_output=True, timeout=5)
    r = subprocess.run([ADB, '-s', DEVICE, 'forward', f'tcp:{PORT}', 'localabstract:scrcpy'],
                       capture_output=True, timeout=5)
    if r.returncode != 0:
        print(f"Forward setup failed: {r.stderr.decode()}")
        return
    
    # Push jar if needed
    subprocess.run([ADB, '-s', DEVICE, 'push',
                    r"D:\Android\QtScrcpy-win-x64-v3.3.3\scrcpy-server", JAR],
                   capture_output=True, timeout=10)
    
    # Start server
    server_cmd = (
        f"CLASSPATH={JAR} "
        "app_process / com.genymobile.scrcpy.Server 3.3.3 "
        "scid=-1 tunnel_forward=true video=true audio=false "
        "control=false max_size=720 video_bit_rate=2000000 "
        "send_device_meta=true send_frame_meta=true "
        "send_dummy_byte=true send_stream_meta=true "
        "cleanup=false power_on=false"
    )
    proc = subprocess.Popen(
        [ADB, '-s', DEVICE, 'shell', server_cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1.5)
    
    # Connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(('127.0.0.1', PORT))
    print(f"Connected to 127.0.0.1:{PORT}")
    
    # Read 65B header
    header = recvall(sock, 65)
    if not header:
        print("No header received")
        return
    dev_name = header[1:].rstrip(b'\x00').decode('utf-8', errors='replace')
    print(f"Device: {dev_name}")
    
    # Read 12B stream meta
    meta = recvall(sock, 12)
    if not meta:
        print("No stream meta")
        return
    codec = meta[:4].decode('ascii')
    w = int.from_bytes(meta[4:8], 'big')
    h = int.from_bytes(meta[8:12], 'big')
    print(f"Stream: {codec} {w}x{h}")
    
    # Parse framed stream
    h264_path = os.path.join(tempfile.gettempdir(), 'scrcpy_test.h264')
    open(h264_path, 'wb').close()
    
    SESSION_FLAG = 1 << 63
    CONFIG_FLAG = 1 << 62  
    KEY_FLAG = 1 << 61
    
    total_data = 0
    frame_count = 0
    t0 = time.time()
    
    while time.time() - t0 < 6 and frame_count < 30:
        fm = recvall(sock, 12)
        if not fm:
            break
        
        pts_flags = int.from_bytes(fm[:8], 'big')
        pkt_size = int.from_bytes(fm[8:12], 'big')
        
        if pkt_size <= 0 or pkt_size > 5 * 1024 * 1024:
            print(f"  Bad pkt_size {pkt_size} (pts={pts_flags:#018x})")
            break
        
        data = recvall(sock, pkt_size)
        if not data:
            break
        
        # Write data
        with open(h264_path, 'ab') as f:
            f.write(data)
        total_data += len(data)
        frame_count += 1
        
        # Parse flags
        is_session = bool(pts_flags & SESSION_FLAG)
        is_config = bool(pts_flags & CONFIG_FLAG)
        is_key = bool(pts_flags & KEY_FLAG)
        pts = pts_flags & ~(SESSION_FLAG | CONFIG_FLAG | KEY_FLAG)
        
        if frame_count <= 3 or frame_count % 50 == 0:
            flags = '|'.join(f for f, v in [('SESSION',is_session),('CONFIG',is_config),('KEY',is_key)] if v)
            print(f"  [{frame_count:3d}] size={pkt_size:6d}, pts={pts} {flags}")
    
    elapsed = time.time() - t0
    print(f"\nCollected {frame_count} frames in {elapsed:.1f}s, {total_data} bytes total")
    
    # NAL analysis
    print("\n=== NAL Analysis ===")
    with open(h264_path, 'rb') as f:
        raw = f.read()
    pos = 0
    nals = []
    while pos < len(raw) - 4:
        if raw[pos:pos+4] == b'\x00\x00\x00\x01':
            nt = raw[pos+4] & 0x1F
            end = pos + 4
            while end < len(raw) - 4:
                if raw[end:end+4] == b'\x00\x00\x00\x01':
                    break
                end += 1
            if end >= len(raw) - 4:
                end = len(raw)
            nals.append((pos, nt, end - pos))
            pos = end
        else:
            pos += 1
    names = {5:'IDR', 6:'SEI', 7:'SPS', 8:'PPS', 9:'AUD'}
    for i, (off, nt, sz) in enumerate(nals[:15]):
        name = names.get(nt, f'?{nt}')
        print(f"  NAL#{i:2d} @{off:6d} type={name} size={sz}")
    
    # OpenCV decode
    print(f"\n=== OpenCV Decode ===")
    cap = cv2.VideoCapture(h264_path, cv2.CAP_FFMPEG)
    decoded = 0
    while decoded < 10:
        ret, frame = cap.read()
        if not ret:
            break
        decoded += 1
        out_path = os.path.join(tempfile.gettempdir(), f'scrcpy_frame_{decoded}.jpg')
        cv2.imwrite(out_path, frame)
        print(f"  Frame {decoded}: {frame.shape[1]}x{frame.shape[0]} saved to {out_path}")
    print(f"Total decoded: {decoded}")
    cap.release()
    
    # Cleanup
    sock.close()
    proc.kill()
    subprocess.run([ADB, '-s', DEVICE, 'forward', '--remove', f'tcp:{PORT}'],
                   capture_output=True, timeout=5)
    print("\nDone!")

if __name__ == '__main__':
    main()
