"""Готовит картинку ZenRead для карточки на лендинге: круг с книгой без белого фона.

Источник — `vibecoding/images/ZenReader.jpg` (квадрат 2048x2054): белый фон,
мягкая тень вокруг и тёмный круглый логотип с книгой по центру. В карточку
нужен только сам круг, поэтому фон и тень вырезаются, а результат кладётся
на прозрачный холст 16:10 (как у остальных карточек).

Как это делается:
  1) по строкам исходника ищутся границы круга и методом наименьших
     квадратов подбирается окружность (cx, cy, R);
  2) по этой окружности строится альфа-маска с мягким краем (рисуется с
     четырёхкратным запасом и уменьшается — так край получается гладким);
  3) круг вписывается в прозрачный холст 800x500 по центру;
  4) результат сохраняется в `dvorzhik.site/images/zenreader.png`.

Запуск:
    python scripts/make_zenreader_logo.py            # собрать картинку
    python scripts/make_zenreader_logo.py --diagnose # только показать подгонку
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT.parent / "vibecoding" / "images" / "ZenReader.jpg"
DEFAULT_OUTPUT = REPO_ROOT / "images" / "zenreader.png"

CANVAS = (800, 500)  # соотношение 16:10 — как у остальных картинок карточек
DARK_LEVEL = 170  # яркость, ниже которой пиксель считаем частью круга
ROW_STEP = 24  # через сколько строк брать замер границы
SUPERSAMPLE = 4  # во сколько раз крупнее рисуем маску для гладкого края
EDGE_INSET = 1.5  # на сколько пикселей срезать белый контур по краю круга


def row_span(lum: Image.Image, y: int) -> tuple[int, int] | None:
    """Возвращает (левый, правый) x тёмной области в строке y."""
    line = lum.crop((0, y, lum.width, y + 1))
    mask = line.point(lambda v: 255 if v < DARK_LEVEL else 0)
    box = mask.getbbox()
    if box is None:
        return None
    return box[0], box[2] - 1


def fit_circle(spans: list[tuple[int, tuple[int, int]]]) -> tuple[float, float, float]:
    """Подбирает окружность (cx, cy, R) по замерам левой и правой границы круга."""
    cx = sum(left + right for _, (left, right) in spans) / (2 * len(spans))

    # Для каждой строки: (y - cy)^2 = R^2 - (x - cx)^2  =>  y^2 + dx^2 = 2*cy*y + (R^2 - cy^2)
    n = len(spans)
    sum_y = sum(y for y, _ in spans)
    sum_yy = sum(y * y for y, _ in spans)
    values = [(y, y * y + (left - cx) ** 2) for y, (left, _) in spans]
    sum_v = sum(v for _, v in values)
    sum_yv = sum(y * v for y, v in values)

    # Решаем систему: n*B + A*sum_y = sum_v ; B*sum_y + A*sum_yy = sum_yv
    det = n * sum_yy - sum_y * sum_y
    a = (n * sum_yv - sum_y * sum_v) / det
    b = (sum_v - a * sum_y) / n
    cy = a / 2
    radius = math.sqrt(b + cy * cy)
    return cx, cy, radius


def measure(source: Path) -> tuple[float, float, float]:
    """Ищет окружность логотипа на исходной картинке."""
    src = Image.open(source).convert("L")
    spans = []
    for y in range(0, src.height, ROW_STEP):
        span = row_span(src, y)
        if span is None or span[1] - span[0] < src.width // 2:
            continue  # строки выше/ниже круга и обрезанные «полки» не годятся
        spans.append((y, span))
    if len(spans) < 5:
        raise RuntimeError("не удалось найти границы круга на исходной картинке")
    return fit_circle(spans)


def build(source: Path, output: Path, diameter: int) -> None:
    """Вырезает круг по найденной окружности и кладёт его на прозрачный холст."""
    cx, cy, radius = measure(source)
    src = Image.open(source).convert("RGB")

    pad = radius + 2
    box = (int(cx - pad), int(cy - pad), int(cx + pad), int(cy + pad))
    side = box[2] - box[0]

    # Кусок исходника вокруг круга; если окружность чуть выходит за кадр,
    # недостающие полосы добираем белым (маска их всё равно срежет).
    crop = Image.new("RGB", (side, side), (255, 255, 255))
    inter = (
        max(0, box[0]),
        max(0, box[1]),
        min(src.width, box[2]),
        min(src.height, box[3]),
    )
    crop.paste(src.crop(inter), (inter[0] - box[0], inter[1] - box[1]))

    # Маска: круг с мягким краем, чуть внутрь — чтобы срезать белый контур.
    big = side * SUPERSAMPLE
    mask = Image.new("L", (big, big), 0)
    r_big = (radius - EDGE_INSET) * SUPERSAMPLE
    c_big = big / 2
    ImageDraw.Draw(mask).ellipse(
        (c_big - r_big, c_big - r_big, c_big + r_big, c_big + r_big), fill=255
    )
    alpha = mask.resize((diameter, diameter), Image.LANCZOS)

    # Под прозрачные пиксели подкладываем тёмный цвет края круга, чтобы при
    # уменьшении не проступал светлый ореол от белого фона исходника.
    edge_color = src.getpixel((int(cx - radius + EDGE_INSET + 3), int(cy)))
    circle = Image.new("RGB", (side, side), edge_color)
    circle.paste(crop, (0, 0), mask.resize((side, side), Image.LANCZOS))
    circle = circle.resize((diameter, diameter), Image.LANCZOS)

    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    logo = circle.convert("RGBA")
    logo.putalpha(alpha)
    canvas.paste(logo, ((CANVAS[0] - diameter) // 2, (CANVAS[1] - diameter) // 2), logo)

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, optimize=True)
    print(
        f"{output.name}: {canvas.size[0]}x{canvas.size[1]}, круг {diameter}px, "
        f"центр исходника ({cx:.1f}, {cy:.1f}), R={radius:.1f}, "
        f"{output.stat().st_size / 1024:.0f} КБ"
    )


def diagnose(source: Path) -> None:
    """Показывает подгонку окружности и максимальное отклонение замеров."""
    src = Image.open(source).convert("L")
    spans = [(y, row_span(src, y)) for y in range(0, src.height, ROW_STEP)]
    spans = [(y, s) for y, s in spans if s and s[1] - s[0] >= src.width // 2]
    cx, cy, radius = fit_circle(spans)
    worst = 0.0
    for y, (left, right) in spans:
        for x in (left, right):
            worst = max(worst, abs(math.hypot(x - cx, y - cy) - radius))
    print(f"исходник {src.size[0]}x{src.size[1]}, замеров {len(spans)}")
    print(f"центр ({cx:.1f}, {cy:.1f}), радиус {radius:.1f}")
    print(f"макс. отклонение замеров от окружности: {worst:.1f}px")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--diameter", type=int, default=int(CANVAS[1] * 0.88))
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()

    if args.diagnose:
        diagnose(args.source)
        return
    build(args.source, args.output, args.diameter)


if __name__ == "__main__":
    main()
