# Прогнозирование спроса и управление товарными запасами в онлайн-ритейле

Аналитический проект на SQL, Python и Power BI: я прошел путь от транзакционных данных до витрины продаж, прогноза спроса, оценки ошибки и сценарных proxy-метрик stockout / overstock risk.

## Что внутри

В этом проекте я работаю с транзакциями онлайн-ритейлера: очищаю данные, отдельно помечаю возвраты и отмененные заказы, собираю ежедневную витрину `sales_date × stock_code × market_id`, строю признаки временного ряда и сравниваю baseline-подходы с моделью прогноза.  
Цель анализа — понять, где прогноз спроса ошибается сильнее всего, какие товары требуют контроля и как на основе прогноза рассчитать сценарные `reorder point` и `safety stock`.  
Важно: в исходных данных нет фактических складских остатков, поэтому stockout и overstock здесь — только сценарные proxy-метрики, а не реальные складские события.

## Power BI dashboard

Dashboard строится на файле `results/dashboard_forecast_inventory.csv`.

### Контроль прогноза

На странице показаны WMAPE, MAE, RMSE, bias, график `actual_sales` vs `forecast_sales`, ошибки по рынкам и ABC/XYZ-сегментам, а также фильтры по `market_id`, `stock_code` и `abc_xyz_segment`.

![Контроль прогноза](assets/dashboard_forecast_control.png)

### Запасы и бизнес-риски

На странице показаны средний `reorder point`, средний `safety stock`, количество сценарных рисков дефицита и избытка, матрица риска по рынкам и сегментам, scatter plot "выручка vs ошибка прогноза" и таблица товаров для контроля.

![Запасы и бизнес-риски](assets/dashboard_inventory_risks.png)

## Бизнес-вопрос

Как на основе исторических транзакций оценить будущий спрос по товарам и рынкам, найти товары с высокой ошибкой прогноза и выделить позиции с риском дефицита или избыточного запаса?

## Данные

Источник: UCI Online Retail II или UCI Online Retail. Файл скачивается вручную и кладется в `data/raw/`.

Ожидаемые поля:

- `Invoice`
- `StockCode`
- `Description`
- `Quantity`
- `InvoiceDate`
- `Price` или `UnitPrice`
- `Customer ID` или `CustomerID`
- `Country`

Основные преобразования:

- `sales_date` из `InvoiceDate`;
- `stock_code` из `StockCode`;
- `market_id` из `Country`;
- `revenue = Quantity × Price/UnitPrice`;
- возвраты и отмененные заказы помечаются отдельным флагом;
- целевая переменная прогноза — `net_sales_qty`.

Сырые данные не хранятся в репозитории.

## Как подготовить данные

1. Скачать UCI Online Retail II или UCI Online Retail.
2. Положить файл в `data/raw/`.
3. Переименовать файл в `online_retail_II.xlsx` или `online_retail.xlsx`.
4. Запустить notebooks по порядку.

## Что сделано

- Загрузка и нормализация транзакционных данных.
- Проверки качества данных: пропуски, отрицательные цены, возвраты, дубли, даты.
- SQL-витрина продаж `sales_date × stock_code × market_id`.
- ABC/XYZ-сегментация товаров.
- Лаговые и rolling-признаки без утечки будущих продаж.
- Baseline-модели: naive, seasonal naive, moving average, median by weekday.
- Модель прогноза спроса.
- Time-series validation с holdout-периодом.
- Метрики WMAPE, MAE, RMSE и bias.
- Сценарная оценка stockout / overstock risk.
- Расчет `reorder point` и `safety stock`.
- Датасет для Power BI dashboard.

## Основные результаты

По расчетным CSV в `results/` лучшая baseline-модель по WMAPE: `median_by_weekday`.

| Подход | WMAPE | MAE | RMSE | bias |
|---|---:|---:|---:|---:|
| Лучшая baseline (`median_by_weekday`) | 0.8574 | 16.4548 | 106.0949 | -0.2835 |
| Модель прогноза | 0.7996 | 15.5885 | 77.1190 | 0.1052 |

На holdout-периоде модель показала меньшую ошибку по WMAPE, MAE и RMSE, но bias изменился по направлению: baseline в среднем занижает спрос, а модель в среднем завышает его.  
Сегменты с наибольшей средней ошибкой в dashboard-датасете: `CZ`, `CX`, `CY`, `BZ`, `AX`.  
Среди строк с высокой абсолютной ошибкой встречаются товары и рынки: `84826 / United Kingdom`, `22197 / United Kingdom`, `23084 / Japan`, `84077 / United Kingdom`.

Сценарный слой запасов выделил группы для контроля: по расчету модели есть `3531` групп с proxy-флагом stockout risk и `6004` групп с proxy-флагом overstock risk из `6837` групп. Это не фактические складские события, а сценарная оценка на основе прогноза и допущения о доступном запасе.

## Структура репозитория

```text
data/        # raw, interim и processed данные; сырые файлы не коммитятся
notebooks/   # пошаговый аналитический сценарий
sql/         # схема, витрины продаж, признаки и inventory-метрики
src/         # Python-модули: проверки, признаки, baseline, модель, метрики, запасы
reports/     # текстовые выводы и инструкции для dashboard
results/     # расчетные CSV после запуска notebooks
assets/      # скриншоты Power BI dashboard
tests/       # unit-тесты ключевой логики
scripts/     # сборка dashboard-датасета
```

## Как запустить проект

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q
```

Если PowerShell блокирует активацию:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Запуск без активации окружения:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Порядок запуска notebooks

1. `notebooks/01_загрузка_и_проверка_данных.ipynb`
2. `notebooks/02_eda_abc_xyz_сегментация.ipynb`
3. `notebooks/03_признаки_baseline_и_валидация.ipynb`
4. `notebooks/04_модель_прогноза_и_ошибка.ipynb`
5. `notebooks/05_запасы_риски_и_бизнес_выводы.ipynb`

После notebooks можно собрать единый датасет для Power BI:

```powershell
python scripts/build_dashboard_dataset.py
```

## Ограничения анализа

- В исходных данных нет фактических складских остатков.
- Stockout и overstock — сценарные proxy-метрики.
- Результаты на holdout не доказывают экономический эффект.
- Качество прогноза зависит от полноты и качества транзакционных данных.
- Возвраты и отмененные заказы могут искажать спрос, поэтому они помечаются отдельно.
- Для практического применения нужны реальные остатки, lead time, закупочные ограничения и стоимость хранения.

## Что этот проект показывает

Я показал, что умею:

- собирать аналитическую витрину из транзакционных данных;
- писать SQL-слой под конкретную бизнес-задачу;
- проверять качество данных;
- строить признаки временного ряда без leakage;
- сравнивать baseline и модель прогноза;
- валидировать прогноз по времени;
- интерпретировать WMAPE, MAE, RMSE и bias;
- переводить прогноз в понятные сценарные метрики для контроля товарных позиций;
- оформлять результат в Power BI dashboard.

## Файлы, которые стоит смотреть

- `README.md`
- `notebooks/`
- `sql/`
- `src/`
- `reports/выводы_для_работодателя.md`
- `reports/dashboard_instructions.md`
- `assets/dashboard_forecast_control.png`
- `assets/dashboard_inventory_risks.png`

## Лицензия

Проект распространяется под лицензией MIT. Подробнее см. файл [LICENSE](LICENSE).
