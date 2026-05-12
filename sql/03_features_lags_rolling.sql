-- Признаки для прогноза спроса: лаги, скользящие средние и календарные поля.

CREATE OR REPLACE VIEW features_lags_rolling AS
SELECT
    date,
    stock_code,
    country,
    sales,
    revenue,
    avg_unit_price,
    invoices,
    customers,
    EXTRACT('dow' FROM date) AS day_of_week,
    EXTRACT('week' FROM date) AS week_of_year,
    EXTRACT('month' FROM date) AS month,
    CASE WHEN EXTRACT('dow' FROM date) IN (0, 6) THEN 1 ELSE 0 END AS is_weekend,
    LAG(sales, 7) OVER (
        PARTITION BY stock_code, country
        ORDER BY date
    ) AS lag_7,
    LAG(sales, 14) OVER (
        PARTITION BY stock_code, country
        ORDER BY date
    ) AS lag_14,
    LAG(sales, 28) OVER (
        PARTITION BY stock_code, country
        ORDER BY date
    ) AS lag_28,
    AVG(sales) OVER (
        PARTITION BY stock_code, country
        ORDER BY date
        ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
    ) AS rolling_mean_7,
    AVG(sales) OVER (
        PARTITION BY stock_code, country
        ORDER BY date
        ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
    ) AS rolling_mean_28
FROM mart_daily_sales;

