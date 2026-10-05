# dvorzhik.site — программы и сервисы

Лендинг с программами и сервисами Александра Дворжицкого (Дворжика):
DrawStory, GeminiPoint, Personal Sky, ZenReader, Yamometer, Yuri Vizbor AI,
а также архив ранних экспериментов.

Сайт — статический (один `index.html` + папка `images`), публикуется через
GitHub Pages на кастомном домене **https://www.dvorzhik.site/**.

## Структура

```
index.html      # лендинг: шапка, карточки программ, подвал
more.html       # страница «Узнать больше» (?id=drawstory, geminipoint, …)
CNAME           # кастомный домен для GitHub Pages: www.dvorzhik.site
images/         # скриншоты и иконки программ
scripts/        # вспомогательные скрипты подготовки картинок
```

## Как добавить новую программу

1. Положите картинку в `images/`.
2. Скопируйте в `index.html` блок `<a class="card">…</a>` из секции
   «Программы», замените картинку, заголовок, описание, бейджи и ссылку.

## Картинки карточек

Обычные карточки используют скриншоты 16:10 (`images/*.jpg`). Если у программы
нет скриншота, а есть только логотип, картинку кладут на прозрачный холст и
подключают с классом `is-logo` — тогда тема не рисует белую подложку:

```html
<img class="card-img is-logo" src="images/zenreader.png" alt="ZenRead" loading="lazy" />
```

Так сделана картинка ZenRead — из `vibecoding/images/ZenReader.jpg` (белый фон
и мягкая тень отрезаются по найденной окружности):

```powershell
python scripts/make_zenreader_logo.py            # собрать images/zenreader.png
python scripts/make_zenreader_logo.py --diagnose # показать подгонку окружности
```

## Локальный просмотр

Достаточно открыть `index.html` в браузере, либо:

```powershell
python -m http.server 8000
```

## Публикация

GitHub Pages настроен на ветку `main`, папку `/ (root)`, с файлом `CNAME`.
Кастомный домен `www.dvorzhik.site` привязан в настройках репозитория
(Settings → Pages).

> Важно: домен `dvorzhik.site` обслуживается DNS-серверами `reg.ru`.
> Чтобы сайт открывался, в панели reg.ru записи `dvorzhik.site` и `www`
> должны указывать на GitHub Pages (A-записи `185.199.108–111.153` и
> CNAME `dvorzhik.github.io`), а редирект на `dvorzhik.ru` — отключён.
> Записи поддоменов `drawstory` и `geminipoint` при этом остаются
> указывать на прежний сервер (`217.149.24.198`).
