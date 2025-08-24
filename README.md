
# UM MVP Importer (One-Site, Selector-Based)

Примітивний імпортер товарів для UkraineMart на базі **одного сайту**.
Парсить каталог → карточки товарів → нормалізує → пише в SQLite і JSON,
автоматично прив'язує товари до **бренд-каталогів**.

## Структура
- `config/example_site.json` — конфіг селекторів.
- `src/main.py` — CLI запускає імпорт.
- `src/connector.py` — лістинг/пагінація/картка.
- `src/normalize.py` — парс ціни, нормалізація, визначення бренду.
- `src/storage.py` — SQLite-схема + upsert + JSON-експорт.
- `config/brand_aliases.json` — синоніми брендів → канонічний бренд.
- `config/brands_seed.json` — базові бренди.

## Quickstart
```
pip install -r requirements.txt
python src/main.py --config config/example_site.json --db um.db --export-json out/products.json
```
Результати: SQLite `um.db`, JSON `out/products.json`.
