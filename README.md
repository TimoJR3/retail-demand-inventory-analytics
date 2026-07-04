# Прогнозирование спроса и сценарные proxy-метрики запасов в онлайн-ритейле

Аналитический проект на SQL, Python, pandas, scikit-learn и Power BI: от historical retail transactions до витрины спроса, прогноза, оценки ошибки и сценарных proxy-метрик stockout / overstock risk.

## Что показывает проект

- Есть historical retail transactions: счета, товары, даты, количество, цена, клиент и страна.
- Строится аналитическая витрина с grain `sales_date x stock_code x market_id`.
- Прогнозируется спрос на уровне товара и рынка.
- Качество прогноза проверяется по WMAPE, MAE, RMSE и bias.
- Stockout и overstock описаны только как proxy-сценарии. Это не реальные складские события, потому что в данных нет фактических остатков.

## Что внутри

В проекте транзакции онлайн-ритейлера очищаются и нормализуются: возвраты и отмененные заказы не удаляются, а помечаются отдельным флагом. Затем собирается ежедневная витрина `sales_date x stock_code x market_id`, строятся признаки временного ряда без утечки будущих продаж и сравниваются baseline-подходы с моделью прогноза.

Цель анализа - понять, где прогноз спроса ошибается сильнее всего, какие товары требуют контроля и как использовать forecast для сценарного расчета `reorder point` и `safety stock`. Проект не обещает реальное управление складом: без фактических остатков, lead time и закупочных ограничений расчеты остаются аналитическими сценариями.

## Бизнес-вопросы

- Где прогноз ошибается сильнее всего: по товарам, рынкам и ABC/XYZ-сегментам.
- Какие товары требуют контроля из-за высокой ошибки, нестабильного спроса или заметного forecast bias.
- Какие рынки дают наибольший вклад в абсолютную ошибку прогноза.
- Как использовать прогноз спроса для сценарных `reorder point` и `safety stock`.
- Где модель лучше baseline, а где простая эвристика может быть надежнее.

## Метрики качества

- **WMAPE** - главная бизнес-метрика для сравнения ошибки с объемом спроса. Полезна, когда важно видеть вклад крупных товарных групп и рынков.
- **MAE** - средняя абсолютная ошибка в штуках. Полезна для понятной интерпретации: насколько прогноз промахивается в среднем.
- **RMSE** - сильнее штрафует крупные ошибки. Полезна для поиска товаров и рынков, где редкие большие промахи особенно опасны.
- **Bias** - среднее направление ошибки. Положительный bias означает завышение прогноза, отрицательный - занижение.

## SQL-слой и grain витрин

SQL-скрипты лежат в `sql/` и пронумерованы в порядке запуска:

1. `01_schema.sql` - логическая схема аналитического слоя.
2. `02_mart_daily_sales.sql` - дневная витрина продаж, grain `sales_date x stock_code x market_id`.
3. `03_features_lags_rolling.sql` - признаки для прогноза на том же grain `sales_date x stock_code x market_id`; lag и rolling-признаки считают только прошлые строки.
4. `04_inventory_metrics.sql` - сценарные proxy-метрики на grain `stock_code x market_id`, рассчитанные из факта, прогноза и простых допущений.

## Power BI dashboard

Dashboard строится на файле `results/dashboard_forecast_inventory.csv`.

### Контроль прогноза

![Контроль прогноза](assets/dashboard_forecast_control.png)

Что показано: WMAPE, MAE, RMSE, bias, динамика `actual_sales` vs `forecast_sales`, ошибки по рынкам и ABC/XYZ-сегментам, фильтры по `market_id`, `stock_code` и `abc_xyz_segment`.

Какую задачу закрывает: помогает быстро найти группы, где forecast требует проверки перед использованием в бизнес-сценариях.

Какой вывод делает аналитик: модель в среднем лучше baseline по WMAPE, MAE и RMSE, но отдельные сегменты и рынки дают непропорционально большой вклад в ошибку.

### Запасы и бизнес-риски

![Запасы и бизнес-риски](assets/dashboard_inventory_risks.png)

Что показано: сценарные `reorder point`, `safety stock`, proxy-флаги stockout / overstock risk, матрица риска по рынкам и сегментам, scatter plot "выручка vs ошибка прогноза" и таблица товаров для контроля.

Какую задачу закрывает: переводит forecast quality в список товарно-рыночных групп, которые стоит проверить вручную.

Какой вывод делает аналитик: proxy-флаги показывают не фактический дефицит или избыток, а сценарные зоны внимания при заданных допущениях.

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
- `revenue = Quantity x Price/UnitPrice`;
- возвраты и отмененные заказы помечаются отдельным флагом;
- целевая переменная прогноза - `net_sales_qty`.

Сырые данные не хранятся в репозитории.

## Что сделано

- Загрузка и нормализация транзакционных данных.
- Проверки качества данных: пропуски, отрицательные цены, возвраты, дубли, даты.
- SQL-витрина продаж `sales_date x stock_code x market_id`.
- ABC/XYZ-сегментация товаров.
- Лаговые и rolling-признаки без утечки будущих продаж.
- Baseline-модели: naive, seasonal naive, moving average, median by weekday.
- Модель прогноза спроса.
- Time-series validation с holdout-периодом.
- Метрики WMAPE, MAE, RMSE и bias.
- Сценарная оценка stockout / overstock risk.
- Сценарный расчет `reorder point` и `safety stock`.
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

Сценарный слой выделил группы для контроля: по расчету модели есть `3531` групп с proxy-флагом stockout risk и `6004` групп с proxy-флагом overstock risk из `6837` групп. Это не фактические складские события, а сценарная оценка на основе прогноза и допущения о доступном запасе.

## Структура репозитория

```text
data/        # raw, interim и processed данные; сырые файлы не коммитятся
notebooks/   # пошаговый аналитический сценарий
sql/         # схема, витрина спроса, признаки и proxy inventory metrics
src/         # Python-модули: проверки, признаки, baseline, модель, метрики, proxy-расчеты
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
```

Если PowerShell блокирует активацию:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Порядок воспроизведения:

1. Скачать UCI Online Retail II или UCI Online Retail.
2. Положить файл в `data/raw/`.
3. Переименовать файл в `online_retail_II.xlsx` или `online_retail.xlsx`.
4. Запустить notebooks по порядку:
   - `notebooks/01_загрузка_и_проверка_данных.ipynb`
   - `notebooks/02_eda_abc_xyz_сегментация.ipynb`
   - `notebooks/03_признаки_baseline_и_валидация.ipynb`
   - `notebooks/04_модель_прогноза_и_ошибка.ipynb`
   - `notebooks/05_запасы_риски_и_бизнес_выводы.ipynb`
5. Проверить SQL-слой в порядке `sql/01_schema.sql` -> `sql/04_inventory_metrics.sql`.
6. Собрать единый датасет для Power BI:

```powershell
python scripts/build_dashboard_dataset.py
```

7. Запустить тесты:

```powershell
python -m pytest -q
```

Запуск без активации окружения:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/build_dashboard_dataset.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Ограничения анализа

- В исходных данных нет фактических складских остатков.
- Stockout и overstock - сценарные proxy-метрики.
- Proxy-флаги не являются подтвержденными событиями склада.
- Результаты на holdout не доказывают экономический эффект.
- Качество прогноза зависит от полноты и качества транзакционных данных.
- Возвраты и отмененные заказы могут искажать спрос, поэтому они помечаются отдельно.
- Для практического применения нужны реальные остатки, lead time, закупочные ограничения, минимальные партии заказа и стоимость хранения.

## Что этот проект показывает

Я показал, что умею:

- собирать аналитическую витрину из транзакционных данных;
- писать SQL-слой под конкретную бизнес-задачу;
- проверять качество данных;
- строить признаки временного ряда без leakage;
- сравнивать baseline и модель прогноза;
- валидировать прогноз по времени;
- интерпретировать WMAPE, MAE, RMSE и bias;
- переводить прогноз в понятные сценарные proxy-метрики для контроля товарных позиций;
- оформлять результат в Power BI dashboard.

## Файлы, которые стоит смотреть

- `README.md`
- `notebooks/`
- `sql/`
- `src/`
- `docs/interview_defense.md`
- `reports/выводы_для_работодателя.md`
- `reports/dashboard_instructions.md`
- `assets/dashboard_forecast_control.png`
- `assets/dashboard_inventory_risks.png`

## Лицензия

Проект распространяется под лицензией MIT. Подробнее см. файл [LICENSE](LICENSE).
