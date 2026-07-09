from PIL import Image
from pathlib import Path

base = Path(__file__).parent
png = base / "assets" / "foxai_logo.png"
ico = base / "assets" / "foxai.ico"

img = Image.open(png).convert("RGBA")
img.save(ico, sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])

print("Created:", ico)