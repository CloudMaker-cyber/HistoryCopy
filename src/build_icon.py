"""生成 exe 图标 icon.ico(蓝色剪贴板),仅在打包时运行。"""

import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "icon.ico")

_PRIMARY = (91, 155, 213, 255)
_PIN = (62, 142, 199, 255)
_WHITE = (255, 255, 255, 255)


def _draw(size: int) -> Image.Image:
    s = size / 256.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def f(v):
        return int(v * s)

    d.rounded_rectangle([f(46), f(15), f(210), f(241)], radius=f(23), fill=_PRIMARY)
    d.rounded_rectangle([f(87), 0, f(169), f(41)], radius=f(15), fill=_PIN)
    for y in (f(97), f(133), f(169)):
        d.rounded_rectangle([f(79), y, f(177), y + f(16)], radius=f(8), fill=_WHITE)
    return img


def main():
    base = _draw(256)
    base.save(OUT, format="ICO",
              sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                     (128, 128), (256, 256)])
    print("已生成图标:", OUT)


if __name__ == "__main__":
    sys.exit(main())
