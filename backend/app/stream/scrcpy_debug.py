"""
Scrcpy debug - read raw socket data
"""
import socket
import subprocess
import time
import os

ADB = r"D:\Android\QtScrcpy-win-x64-v3.3.3\adb.exe"
DEVICE = "192.168.100.5:5555"
PORT = 27191

# Clean
subprocess.run([ADB, '-s', DEVICE, 'forward', '--remove', f'tcp:{PORT}'],
               capture_output=True, timeout=5)
time.sleep(0.3)

# Set up forward
subprocess.run([ADB, '-s', DEVICE, 'forward', f'tcp:{PORT}', 'localabstract:scrcpy'],
               capture_output=True, timeout=5)
print(f"Forward tcp:{PORT} → localabstract:scrcpy")

# Start server
server_cmd = (
    "CLASSPATH=/data/local/tmp/scrcpy-server "
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
print("Server started, waiting 1.5s...")
time.sleep(1.5)

# Connect
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3)
sock.connect(('127.0.0.1', PORT))
print("Connected!")

# Read exactly 65 bytes (header)
header = b''
while len(header) < 65:
    chunk = sock.recv(65 - len(header))
    if not chunk:
        break
    header += chunk

print(f"Header: {len(header)} bytes")
dev_name = header[1:65].rstrip(b'\x00').decode('utf-8', errors='replace')
print(f"Dummy: {header[0]:#04x}, Device: '{dev_name}'")

# Now try to read with SHORT timeout (500ms) to see what comes next
sock.settimeout(0.5)

# Read whatever is available for 3 seconds
t0 = time.time()
total_next = 0
while time.time() - t0 < 3:
    try:
        chunk = sock.recv(4096)
        if not chunk:
            print("Connection closed")
            break
        total_next += len(chunk)
        print(f"  Got {len(chunk):5d} bytes (total: {total_next:5d}) [{chunk[:8].hex()}...]")
    except socket.timeout:
        print(f"  Timeout (total so far: {total_next})")
        break

print(f"\nTotal data after header: {total_next} bytes")
sock.close()
proc.kill()

# Clean up forward
subprocess.run([ADB, '-s', DEVICE, 'forward', '--remove', f'tcp:{PORT}'],
               capture_output=True, timeout=5)
