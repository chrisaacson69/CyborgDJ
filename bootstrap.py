import pathlib, base64, sys
b64 = sys.stdin.buffer.read()
script = base64.b64decode(b64)
target = pathlib.Path("C:/Users/Chris.Isaacson/source/repos/cyborgdj/spectral_terrain.py")
target.write_bytes(script)
print(f"Written {len(script)} bytes")
