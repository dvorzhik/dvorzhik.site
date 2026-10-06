"""Готовит картинку карточки лендинга: любой исходник —> холст 11:6 (1100x600).

Карточки показывают картинку в рамке 11:6 (`object-fit: cover`), поэтому файл
лучше заранее привести к 11:6 — тогда CSS ничего не обрежет. Скрипт вписывает
исходник в холст целиком (по длинной стороне) и доливает свободные полосы
цветом, усреднённым по краям исходника: для однотонных фонов (тёмный фон
GeminiPoint, кремовый фон страницы Визбора, бумажный фон SeaBlitz) шва не
видно, а важное содержимое не срезается — в отличие от центр-кропа. Если
исходник уже в пропорции 11:6 (например 1024x559), он просто масштабируется
до холста 1100x600 — без полос и без кропа.

Запуск:
    python scripts/make_card_image.py --source <исходник> --output <куда сохранить>
    python scripts/make_card_image.py --source ../sunset/images/GP.png \
        --output images/geminipoint.jpg --fill mirror
    python scripts/make_card_image.py --source ../sunset/images/GP.png --diagnose

Ключи:
    --fill edges  (по умолчанию) каждая полоса берёт цвет своего края исходника;
    --fill top | bottom         все полосы красятся цветом одного края — удобно,
                                когда у нижнего края есть текст и его средний
                                цвет «грязный» (страница Визбора);
    --fill mirror               полосы отражают прилегающий край картинки — на
                                градиентных фонах (небо и песок Yamometer) шва
                                не видно вовсе, но у самого края не должно быть
                                текста, иначе он задвоится;
    --diagnose                  показать расчёт, ничего не записывая.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

CANVAS = (1100, 600)  # соотношение 11:6 — как у остальных картинок карточек
BAND_SAMPLE = 6  # сколько краевых строк исходника усредняем для цвета полос
SNAP_TOLERANCE = 0.005  # если исходник отличается от холста меньше чем на 0.5%, полосы не нужны
JPEG_QUALITY = 90


def mean_edge_color(img: Image.Image, edge: str, rows: int = BAND_SAMPLE) -> tuple[int, int, int]:
    """Средний цвет полосы исходника у указанного края (top/bottom/left/right)."""
    if edge == "top":
        box = (0, 0, img.width, rows)
    elif edge == "bottom":
        box = (0, img.height - rows, img.width, img.height)
    elif edge == "left":
        box = (0, 0, rows, img.height)
    else:
        box = (img.width - rows, 0, img.width, img.height)

    # Уменьшение полосы до одного пикселя фильтром BOX даёт её средний цвет.
    return img.crop(box).resize((1, 1), Image.BOX).getpixel((0, 0))


def fit_size(src: Image.Image, canvas: tuple[int, int]) -> tuple[int, int]:
    """Размер, в который исходник влезает целиком, с сохранением пропорций."""
    scale = min(canvas[0] / src.width, canvas[1] / src.height)
    return round(src.width * scale), round(src.height * scale)


def band_color(img: Image.Image, edge: str, fill: str) -> tuple[int, int, int]:
    """Цвет полосы у края `edge` с учётом режима --fill."""
    return mean_edge_color(img, fill if fill in ("top", "bottom") else edge)


def mirrored_band(fitted: Image.Image, edge: str, width: int, height: int) -> Image.Image | None:
    """Полоса-отражение прилегающего края картинки — продолжает градиент без шва.

    Отражение возможно, только если полоса целиком помещается на картинке;
    иначе возвращаем None, и вызывающий код заливает полосу средним цветом.
    """
    if edge in ("top", "bottom") and width == fitted.width and height <= fitted.height:
        rows = (0, 0, fitted.width, height) if edge == "top" else (0, fitted.height - height, fitted.width, fitted.height)
        return ImageOps.flip(fitted.crop(rows))
    if edge in ("left", "right") and height == fitted.height and width <= fitted.width:
        cols = (0, 0, width, fitted.height) if edge == "left" else (fitted.width - width, 0, fitted.width, fitted.height)
        return ImageOps.mirror(fitted.crop(cols))
    return None


def same_ratio(src: Image.Image, canvas: tuple[int, int]) -> bool:
    """Исходник уже в пропорции холста (с точностью SNAP_TOLERANCE)."""
    return abs(src.width / src.height - canvas[0] / canvas[1]) <= SNAP_TOLERANCE * canvas[0] / canvas[1]


def build(source: Path, output: Path, canvas: tuple[int, int], fill: str) -> None:
    src = Image.open(source).convert("RGB")

    if same_ratio(src, canvas):
        # Исходник уже нужной пропорции (например 1024x559): полосы получились бы
        # шириной в пиксель, поэтому просто масштабируем картинку до холста.
        picture = src.resize(canvas, Image.LANCZOS)
        details = "исходник уже 11:6 — масштабирован до холста без полос"
    else:
        fitted = src.resize(fit_size(src, canvas), Image.LANCZOS)

        left = (canvas[0] - fitted.width) // 2
        top = (canvas[1] - fitted.height) // 2

        picture = Image.new("RGB", canvas, band_color(src, "top", fill))
        picture.paste(fitted, (left, top))

        # Свободные полосы по краям холста: отражение края (--fill mirror) или заливка
        # цветом соответствующего края исходника.
        bands = {
            "top": (0, 0, canvas[0], top),
            "bottom": (0, top + fitted.height, canvas[0], canvas[1]),
            "left": (0, 0, left, canvas[1]),
            "right": (left + fitted.width, 0, canvas[0], canvas[1]),
        }
        for edge, box in bands.items():
            width, height = box[2] - box[0], box[3] - box[1]
            if width <= 0 or height <= 0:
                continue
            band = mirrored_band(fitted, edge, width, height) if fill == "mirror" else None
            picture.paste(band or Image.new("RGB", (width, height), band_color(src, edge, fill)), box[:2])

        details = (
            f"исходник {src.width}x{src.height} -> {fitted.width}x{fitted.height}, полосы "
            f"{canvas[0] - fitted.width}px по бокам и {canvas[1] - fitted.height}px сверху/снизу"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    picture.save(output, quality=JPEG_QUALITY, optimize=True, progressive=True)
    print(f"{output.name}: {picture.size[0]}x{picture.size[1]} ({details}, {output.stat().st_size / 1024:.0f} КБ)")


def diagnose(source: Path, canvas: tuple[int, int], fill: str) -> None:
    """Показывает, как исходник ляжет на холст, ничего не записывая."""
    src = Image.open(source).convert("RGB")
    print(f"исходник {src.width}x{src.height} (соотношение {src.width / src.height:.3f})")
    print(f"холст {canvas[0]}x{canvas[1]} (соотношение {canvas[0] / canvas[1]:.3f})")
    if same_ratio(src, canvas):
        print("пропорции совпадают — картинка будет просто масштабирована до холста, полос не будет")
        return
    fitted = fit_size(src, canvas)
    print(f"картинка на холсте: {fitted[0]}x{fitted[1]}")
    print(f"полосы: по бокам {canvas[0] - fitted[0]}px, сверху/снизу {canvas[1] - fitted[1]}px")
    if fill == "mirror":
        print("цвет полос: отражение края картинки (--fill mirror)")
    else:
        print(f"цвет полос (--fill {fill}): сверху {band_color(src, 'top', fill)}, снизу {band_color(src, 'bottom', fill)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True, help="исходник любого размера")
    parser.add_argument("--output", type=Path, help="куда сохранить картинку 11:6 (нужно без --diagnose)")
    parser.add_argument("--canvas", default=f"{CANVAS[0]}x{CANVAS[1]}", help="размер холста, по умолчанию 1100x600")
    parser.add_argument(
        "--fill",
        choices=("edges", "top", "bottom", "mirror"),
        default="edges",
        help="чем заполнять полосы: цветом края (edges), одним из краёв (top/bottom) или отражением (mirror)",
    )
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()

    width, height = (int(part) for part in args.canvas.lower().split("x"))
    canvas = (width, height)

    if args.diagnose:
        diagnose(args.source, canvas, args.fill)
        return
    if args.output is None:
        parser.error("нужен --output (или запустите с --diagnose, чтобы только посмотреть расчёт)")
    build(args.source, args.output, canvas, args.fill)


if __name__ == "__main__":
    main()
