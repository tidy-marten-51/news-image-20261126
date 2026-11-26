#!/usr/bin/env python3
"""Draw a newspaper front page summing up world news of Thursday 26 November 2026.

Pure Python 3 standard library: a small raster canvas, a 5x7 bitmap font stored
as integer bitmasks, and a hand-written PNG encoder (zlib + struct). No network,
no randomness, no clock anywhere in the image, so two runs are byte-identical.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   -> writes out/entry.png
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024


def rgb(r, g, b):
    return bytes((r, g, b))


PAPER = rgb(248, 243, 232)   # warm newsprint
INK = rgb(22, 22, 22)       # near-black
RED = rgb(168, 30, 35)      # headline red
BLUE = rgb(31, 58, 95)      # deep blue
NAVY = rgb(18, 32, 64)      # night sky
SKY = rgb(188, 211, 232)    # pale sky
STEEL = rgb(91, 107, 125)   # building grey-blue
GREY = rgb(92, 92, 92)
LIGHT = rgb(233, 225, 205)  # panel fill
GREEN = rgb(46, 125, 50)
BROWN = rgb(122, 74, 33)
GOLD = rgb(201, 138, 27)
WAVE = rgb(47, 111, 178)
WHITE = rgb(255, 255, 255)
ORANGE = rgb(214, 106, 32)
TEAL = rgb(32, 122, 110)


# ------------------------------------------------------------- 5x7 font ----
# Each glyph is 7 rows; each row is a 5-bit integer, bit 4 = leftmost column.
# Uppercase letters, digits and punctuation only: the page is set in caps.
FONT = {
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 27, 17),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 6, 8, 16, 31),
    "3": (31, 2, 4, 2, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 12, 12),
    ",": (0, 0, 0, 0, 12, 4, 8),
    ":": (0, 12, 12, 0, 12, 12, 0),
    ";": (0, 12, 12, 0, 12, 4, 8),
    "'": (4, 4, 8, 0, 0, 0, 0),
    "-": (0, 0, 0, 14, 0, 0, 0),
    "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8),
    "/": (1, 2, 2, 4, 8, 8, 16),
    "&": (12, 18, 20, 8, 21, 18, 13),
    "%": (25, 26, 2, 4, 8, 11, 19),
    "$": (4, 15, 20, 14, 5, 30, 4),
    "!": (4, 4, 4, 4, 4, 0, 4),
    "?": (14, 17, 1, 6, 4, 0, 4),
    "=": (0, 0, 31, 0, 31, 0, 0),
    "+": (0, 4, 4, 31, 4, 4, 0),
    "*": (0, 21, 14, 31, 14, 21, 0),
}

BLANK = (0, 0, 0, 0, 0, 0, 0)


# ---------------------------------------------------------------- canvas ----
class Canvas:
    """A flat RGB canvas with a few vector helpers and bitmap text."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(bg * (w * h))

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = c

    def box(self, x, y, w, h, c):
        assert len(c) == 3, "colour must be 3 bytes"
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = c * (x1 - x0)
        n = (x1 - x0) * 3
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + n] = row

    def hline(self, x, y, w, c, thick=1):
        self.box(x, y, w, thick, c)

    def vline(self, x, y, h, c, thick=1):
        self.box(x, y, thick, h, c)

    def seg(self, x1, y1, x2, y2, c, thick=1):
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy), 1)
        half = thick // 2
        for s in range(steps + 1):
            x = int(round(x1 + dx * s / steps))
            y = int(round(y1 + dy * s / steps))
            self.box(x - half, y - half, thick, thick, c)

    def disc(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            half = math.isqrt(max(0, r * r - dy * dy))
            self.box(cx - half, cy + dy, 2 * half + 1, 1, c)

    def ring(self, cx, cy, r, c, thick=2):
        for dy in range(-r, r + 1):
            half = math.isqrt(max(0, r * r - dy * dy))
            self.box(cx - half, cy + dy, thick, 1, c)
            self.box(cx + half - thick + 1, cy + dy, thick, 1, c)
        for dx in range(-r, r + 1):
            half = math.isqrt(max(0, r * r - dx * dx))
            self.box(cx + dx, cy - half, 1, thick, c)
            self.box(cx + dx, cy + half - thick + 1, 1, thick, c)

    def triangle(self, pts, c):
        (x1, y1), (x2, y2), (x3, y3) = sorted(pts, key=lambda p: p[1])

        def edge(xa, ya, xb, yb, y):
            if yb == ya:
                return float(xa)
            return xa + (xb - xa) * (y - ya) / (yb - ya)

        for y in range(y1, y3 + 1):
            if y < y2:
                xa = edge(x1, y1, x2, y2, y)
                xb = edge(x1, y1, x3, y3, y)
            else:
                xa = edge(x2, y2, x3, y3, y)
                xb = edge(x1, y1, x3, y3, y)
            x0 = int(min(xa, xb))
            x1x = int(max(xa, xb))
            self.box(x0, y, x1x - x0 + 1, 1, c)

    # ------------------------------------------------------------ text ----
    def text_w(self, s, scale):
        return len(s) * 6 * scale - scale

    def text(self, x, y, s, scale, c, bold=False):
        cx = x
        extra = max(1, scale // 3) if bold else 0
        for ch in s:
            rows = FONT.get(ch, BLANK)
            for r, bits in enumerate(rows):
                for col in range(5):
                    if bits >> (4 - col) & 1:
                        self.box(cx + col * scale, y + r * scale,
                                 scale, scale, c)
                        if extra:
                            self.box(cx + col * scale + extra,
                                     y + r * scale, scale, scale, c)
            cx += 6 * scale
        return cx

    def centred(self, y, s, scale, c, bold=False):
        self.text((self.w - self.text_w(s, scale)) // 2, y, s, scale, c, bold)

    def wrap(self, s, scale, maxw):
        lines = []
        cur = ""
        for word in s.split(" "):
            trial = (cur + " " + word).strip() if cur else word
            if self.text_w(trial, scale) <= maxw:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, scale, maxw, c, leading=None, bold=False):
        step = leading if leading is not None else 9 * scale
        for ln in self.wrap(s, scale, maxw):
            self.text(x, y, ln, scale, c, bold)
            y += step
        return y


# ------------------------------------------------------------ PNG writer ----
def encode_png(w, h, buf):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter: none
        raw += buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# --------------------------------------------------------- illustrations ----
def draw_ship(cv, x, y, w, h):
    """A container ship under a big 25% badge: the tariff story."""
    cv.box(x, y, w, h, SKY)
    cv.disc(x + w - 52, y + 30, 20, GOLD)          # low sun
    # sea
    for wy in (y + h - 18, y + h - 6):
        for wx in range(x, x + w, 26):
            cv.disc(wx + 13, wy, 11, WAVE)
        cv.box(x, wy, w, 11, WAVE)
    # hull
    hx, hy = x + 14, y + h - 78
    cv.triangle([(hx, hy), (hx + w - 110, hy),
                 (hx + w - 130, hy + 30)], INK)
    cv.box(hx, hy, w - 110, 30, INK)
    # containers
    cv.box(hx + 10, hy - 32, 52, 32, RED)
    cv.box(hx + 66, hy - 32, 52, 32, GOLD)
    cv.box(hx + 122, hy - 32, 52, 32, BLUE)
    cv.box(hx + 178, hy - 32, 52, 32, TEAL)
    # bridge
    cv.box(hx + w - 150, hy - 56, 34, 56, WHITE)
    cv.box(hx + w - 144, hy - 50, 10, 12, INK)
    cv.box(hx + w - 128, hy - 50, 10, 12, INK)
    # the rate, in a red disc
    bx, by = x + w - 62, y + h - 128
    cv.disc(bx, by, 44, RED)
    cv.ring(bx, by, 44, WHITE, 3)
    cv.text(bx - 30, by - 14, "25%", 3, WHITE, bold=True)


def draw_rocket(cv, x, y, w, h):
    """A rocket climbing to a ringed station: the Tiangong first."""
    cv.box(x, y, w, h, NAVY)
    for sx, sy in ((x + 24, y + 18), (x + w - 30, y + 26), (x + 60, y + 44),
                   (x + w - 70, y + 58), (x + 40, y + 80), (x + w - 44, y + 96)):
        cv.disc(sx, sy, 2, WHITE)
    # station ring, upper right
    sx, sy = x + w - 62, y + 30
    cv.ring(sx, sy, 20, GOLD, 4)
    cv.box(sx - 34, sy - 4, 14, 8, WHITE)
    cv.box(sx + 20, sy - 4, 14, 8, WHITE)
    cv.disc(sx, sy, 8, WHITE)
    # rocket body
    rx = x + w // 2 - 14
    ry = y + 34
    cv.box(rx, ry, 28, 62, WHITE)
    cv.triangle([(rx, ry), (rx + 28, ry), (rx + 14, ry - 22)], RED)
    cv.box(rx - 10, ry + 44, 10, 18, RED)
    cv.box(rx + 28, ry + 44, 10, 18, RED)
    cv.disc(rx + 14, ry + 30, 6, BLUE)
    # flame
    cv.triangle([(rx + 4, ry + 62), (rx + 24, ry + 62),
                 (rx + 14, ry + 96)], ORANGE)
    cv.triangle([(rx + 8, ry + 62), (rx + 20, ry + 62),
                 (rx + 14, ry + 84)], GOLD)


def draw_plane(cv, x, y, w, h):
    """A plane above a snaking queue: Thanksgiving travel chaos."""
    cv.box(x, y, w, h, SKY)
    cv.disc(x + 40, y + 22, 10, WHITE)
    cv.disc(x + 70, y + 30, 7, WHITE)
    cv.disc(x + w - 50, y + 18, 8, WHITE)
    # plane
    px, py = x + w // 2 - 90, y + 26
    cv.box(px, py, 180, 16, WHITE)
    cv.triangle([(px + 180, py), (px + 214, py + 8), (px + 180, py + 16)],
                WHITE)
    cv.triangle([(px + 60, py), (px + 90, py - 22), (px + 104, py)], WHITE)
    cv.triangle([(px + 10, py + 16), (px + 30, py + 34), (px + 44, py + 16)],
                WHITE)
    cv.box(px + 8, py + 4, 26, 8, BLUE)
    cv.box(px, py + 12, 180, 4, BLUE)          # cheatline, for contrast
    cv.triangle([(px + 150, py), (px + 168, py - 18), (px + 178, py)], BLUE)
    # queue of travellers below
    qy = y + h - 26
    for i in range(9):
        qx = x + 26 + i * 30
        cv.disc(qx, qy - 12, 6, INK if i % 2 == 0 else RED)
        cv.box(qx - 5, qy - 5, 10, 14, INK if i % 2 == 0 else RED)
    cv.box(x + 14, qy + 10, w - 28, 3, INK)


def draw_boat(cv, x, y, w, h):
    """A crowded small boat on open water: the Canary Islands record."""
    cv.box(x, y, w, h, SKY)
    cv.disc(x + w - 44, y + 24, 16, GOLD)
    # sea
    for wy in (y + h - 20, y + h - 8):
        for wx in range(x, x + w, 26):
            cv.disc(wx + 13, wy, 11, WAVE)
        cv.box(x, wy, w, 11, WAVE)
    # boat hull
    bx, by = x + w // 2 - 96, y + h - 62
    cv.triangle([(bx, by), (bx + 192, by), (bx + 168, by + 26)], BROWN)
    cv.box(bx, by, 192, 26, BROWN)
    cv.box(bx + 8, by - 8, 176, 8, GOLD)
    # people aboard
    for i in range(7):
        px = bx + 22 + i * 24
        cv.disc(px, by - 16, 6, RED if i % 3 == 0 else BLUE)
        cv.box(px - 5, by - 9, 10, 10, RED if i % 3 == 0 else BLUE)
    # small sail
    cv.vline(bx + 96, by - 58, 50, INK, 3)
    cv.triangle([(bx + 99, by - 56), (bx + 99, by - 14),
                 (bx + 148, by - 14)], WHITE)


def draw_chip(cv, x, y, w, h):
    """A processor with pins and circuit traces: the Nvidia story."""
    cv.box(x, y, w, h, LIGHT)
    cx, cy = x + w // 2, y + h // 2
    # pins
    for i in range(5):
        off = -40 + i * 20
        cv.box(cx + off - 3, cy - 52, 6, 12, INK)
        cv.box(cx + off - 3, cy + 40, 6, 12, INK)
        cv.box(cx - 52, cy + off - 3, 12, 6, INK)
        cv.box(cx + 40, cy + off - 3, 12, 6, INK)
    # die
    cv.box(cx - 40, cy - 40, 80, 80, INK)
    cv.box(cx - 32, cy - 32, 64, 64, BLUE)
    cv.text(cx - 18, cy - 12, "AI", 3, WHITE, bold=True)
    # traces out to the edges
    cv.hline(x + 10, cy - 46, 34, GREEN, 3)
    cv.hline(x + w - 44, cy + 46, 34, GREEN, 3)
    cv.vline(cx - 46, y + 8, 30, GREEN, 3)
    cv.vline(cx + 46, y + h - 38, 30, GREEN, 3)


def draw_port(cv, x, y, w, h):
    """A dock crane over containers, smoke rising: the Houthi threat."""
    cv.box(x, y, w, h, SKY)
    # smoke plume
    for i, (sx, sy, sr) in enumerate(((x + w - 70, y + 16, 12),
                                      (x + w - 88, y + 30, 16),
                                      (x + w - 66, y + 44, 20))):
        cv.disc(sx, sy, sr, GREY)
    # crane
    cv.vline(x + 30, y + 10, h - 30, INK, 6)
    cv.hline(x + 30, y + 14, w - 60, INK, 6)
    cv.seg(x + 30, y + 14, x + 70, y + 52, INK, 4)
    cv.vline(x + w - 52, y + 20, 34, INK, 3)
    cv.box(x + w - 66, y + 54, 28, 16, RED)
    # containers on the dock
    cy = y + h - 34
    cv.box(x + 16, cy, 64, 26, BLUE)
    cv.box(x + 84, cy, 64, 26, GOLD)
    cv.box(x + 152, cy, 64, 26, RED)
    cv.box(x + 48, cy - 26, 64, 26, TEAL)
    cv.box(x, cy + 26, w, 8, INK)


def draw_flags(cv, x, y, w, h):
    """Two flags on one pole pair, shaking hands below: the Pacific pact."""
    cv.box(x, y, w, h, LIGHT)
    # poles
    cv.vline(x + 60, y + 12, 74, INK, 4)
    cv.vline(x + w - 64, y + 12, 74, INK, 4)
    # left flag: blue field, white stars
    cv.box(x + 64, y + 12, 84, 44, BLUE)
    for sx, sy in ((x + 84, y + 26), (x + 112, y + 22), (x + 132, y + 40),
                   (x + 96, y + 44)):
        cv.disc(sx, sy, 3, WHITE)
    # right flag: green field, gold disc
    cv.box(x + w - 148, y + 12, 84, 44, GREEN)
    cv.disc(x + w - 106, y + 34, 12, GOLD)
    # handshake: two forearms meeting level at the centre
    hy = y + h - 30
    cv.box(x + 30, hy - 14, 96, 10, INK)
    cv.box(x + w - 126, hy - 14, 96, 10, INK)
    cv.disc(x + w // 2, hy - 9, 13, INK)
    cv.box(x + 22, hy - 18, 22, 18, RED)
    cv.box(x + w - 44, hy - 18, 22, 18, BLUE)


# -------------------------------------------------------------- page ----
def story_card(cv, x, y, w, kicker, headline, standfirst, draw_fn):
    """One secondary story: kicker, headline, illustration, standfirst."""
    cv.text(x, y, kicker, 1, RED, bold=True)
    y += 16
    y = cv.para(x, y, headline, 2, w, INK, leading=20, bold=True)
    y += 6
    draw_fn(cv, x, y, w, 118)
    y += 118 + 8
    y = cv.para(x, y, standfirst, 1, w, GREY, leading=10)
    return y


def build_page():
    cv = Canvas(W, H, PAPER)

    # ---- masthead ----
    cv.hline(24, 16, W - 48, INK, 4)
    cv.centred(30, "THE WORLD", 8, INK, bold=True)
    cv.centred(96, "THURSDAY 26 NOVEMBER 2026", 2, INK, bold=True)
    cv.hline(24, 124, W - 48, INK, 3)
    cv.hline(24, 130, W - 48, INK, 1)

    # ---- summary strip ----
    cv.centred(146, "US HITS INDIA WITH 25% TARIFFS - PAKISTANI ASTRONAUT IN ORBIT", 1, INK)
    cv.centred(160, "THANKSGIVING TRAVEL CHAOS - RECORD MIGRANT ARRIVALS IN CANARIES", 1, INK)
    cv.hline(24, 178, W - 48, INK, 2)

    # ---- lead story ----
    lx, lw = 24, 596
    cv.text(lx, 196, "LEAD STORY - WASHINGTON", 1, RED, bold=True)
    y = 214
    for ln in ("US PROPOSES 25%", "TARIFFS ON INDIA"):
        cv.text(lx, y, ln, 4, INK, bold=True)
        y += 36
    y += 8
    y = cv.para(lx, y,
                "WASHINGTON PROPOSES DUTIES OF UP TO 25 PER CENT ON "
                "GOODS FROM INDIA UNLESS A TRADE DEAL IS REACHED. THE "
                "RATE COULD FALL TO 17 PER CENT IF TALKS SUCCEED.",
                2, lw, INK, leading=20)
    y += 12
    cv.text(lx, y, "WASHINGTON - 26 NOVEMBER 2026", 1, GREY, bold=True)
    draw_ship(cv, 644, 196, 356, 250)
    cv.text(644, 452, "A CONTAINER SHIP AT SEA", 1, GREY)
    cv.hline(24, 482, W - 48, INK, 2)

    # ---- secondary stories, two rows of three ----
    col_w = 312
    gap = 20
    xs = [24, 24 + col_w + gap, 24 + 2 * (col_w + gap)]
    row1_y = 500
    story_card(cv, xs[0], row1_y, col_w, "SPACE - AP",
               "FIRST PAKISTANI ASTRONAUT REACHES TIANGONG",
               "MUHAMMAD ZEESHAN ALI BECOMES THE FIRST FOREIGN "
               "ASTRONAUT TO FLY TO CHINA'S TIANGONG STATION ABOARD "
               "SHENZHOU-24.", draw_rocket)
    story_card(cv, xs[1], row1_y, col_w, "UNITED STATES - AP",
               "THANKSGIVING TRAVEL IN CHAOS AS QUEUES GROW",
               "TRAVELLERS FACE LONG AIRPORT QUEUES AND BAD WEATHER IN "
               "THE RUN-UP TO THANKSGIVING.", draw_plane)
    story_card(cv, xs[2], row1_y, col_w, "SPAIN - AP",
               "RECORD MIGRANT ARRIVALS IN CANARY ISLANDS",
               "NEARLY 2,000 MIGRANTS ARRIVE IN SPAIN'S CANARY ISLANDS "
               "IN A SINGLE DAY, A RECORD.", draw_boat)
    cv.hline(24, 742, W - 48, INK, 1)

    row2_y = 756
    story_card(cv, xs[0], row2_y, col_w, "TECHNOLOGY - AP",
               "VANCE DEFENDS NVIDIA CHIEF HUANG",
               "VICE-PRESIDENT VANCE DEFENDS NVIDIA CHIEF JENSEN HUANG "
               "AS WASHINGTON'S SCRUTINY GROWS.", draw_chip)
    story_card(cv, xs[1], row2_y, col_w, "MIDDLE EAST - AP",
               "HOUTHIS VOW REVENGE AFTER PORT CITY HIT",
               "THE HOUTHIS THREATEN RETALIATION AFTER A PORT CITY IS "
               "HIT.", draw_port)
    story_card(cv, xs[2], row2_y, col_w, "ASIA-PACIFIC - AP",
               "AUSTRALIA AND SOLOMON ISLANDS SIGN SECURITY PACT",
               "AUSTRALIA AND SOLOMON ISLANDS SIGN A SECURITY PACT SEEN "
               "AS A CHECK ON CHINA.", draw_flags)

    # ---- footer ----
    cv.hline(24, 994, W - 48, INK, 2)
    cv.centred(1004, "ALL STORIES REPORTED 26 NOVEMBER 2026 - SOURCES: AP, AFP", 1, GREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build_page()
    data = encode_png(W, H, cv.buf)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
