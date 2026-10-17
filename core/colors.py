def rainbow_into(buf, offset, hue):
    """Write a fully saturated RGB hue without allocating a color list."""
    hue %= 360
    sector = hue // 60
    up = (hue % 60) * 255 // 60
    down = 255 - up
    if sector == 0:
        r, g, b = 255, up, 0
    elif sector == 1:
        r, g, b = down, 255, 0
    elif sector == 2:
        r, g, b = 0, 255, up
    elif sector == 3:
        r, g, b = 0, down, 255
    elif sector == 4:
        r, g, b = up, 0, 255
    else:
        r, g, b = 255, 0, down
    buf[offset] = r
    buf[offset + 1] = g
    buf[offset + 2] = b


def rainbow_palette():
    """Precompute all integer hues once, for native renderers (1080 bytes)."""
    palette = bytearray(360 * 3)
    for hue in range(360):
        rainbow_into(palette, hue * 3, hue)
    return palette


def hsv_into(buf, offset, hue, saturation, value):
    """HSV with integer hue and saturation/value in 0..255."""
    hue %= 360
    sector = hue // 60
    f = hue % 60
    p = value * (255 - saturation) // 255
    q = value * (15300 - f * saturation) // 15300
    t = value * (15300 - (60 - f) * saturation) // 15300
    if sector == 0:
        r, g, b = value, t, p
    elif sector == 1:
        r, g, b = q, value, p
    elif sector == 2:
        r, g, b = p, value, t
    elif sector == 3:
        r, g, b = p, q, value
    elif sector == 4:
        r, g, b = t, p, value
    else:
        r, g, b = value, p, q
    buf[offset], buf[offset + 1], buf[offset + 2] = r, g, b
