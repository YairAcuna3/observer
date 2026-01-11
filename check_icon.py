from PIL import Image

img = Image.open('media/icon.ico')
print(f"Mode: {img.mode}")
print(f"Size: {img.size}")
print(f"Format: {img.format}")

img_rgba = img.convert('RGBA')
alpha = img_rgba.getchannel("A")
print(f"Alpha range: {alpha.getextrema()}")

# Ver si tiene transparencia real
if alpha.getextrema()[0] == 255:
    print("El icono NO tiene transparencia (alpha siempre 255)")
else:
    print("El icono SÍ tiene transparencia")
