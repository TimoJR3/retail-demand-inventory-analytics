-- Признаки для прогноза спроса на уровне sales_date x stock_code x market_id.
-- Важно: все rolling-признаки используют только прошлые строки:
-- ROWS BETWEEN N PRECEDING AND 1 PRECEDING.
-- Текущая и будущая продажа не должны попадать в признаки, иначе оценка прогноза
-- будет завышена из-за утечки целевой переменной.

CREATE OR REPLACE VIEW features_lags_rolling AS
WITH ordered AS (
    SELECT
        sales_date,
        stock_code,
        description,
        market_id,
        sales_qty,
        avg_unit_price,
        revenue,
        invoices_cnt,
        customers_cnt,
        returns_qty,
        net_sales_qty,
        weekday,
        month,
        year,
        is_weekend,
        is_return_flag,
        is_price_missing,
        ROW_NUMBER() OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
        ) AS row_num
    FROM mart_daily_sales
),
history AS (
    SELECT
        *,
        LAG(net_sales_qty, 7) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
        ) AS lag_7,
        LAG(net_sales_qty, 14) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
        ) AS lag_14,
        LAG(net_sales_qty, 28) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
        ) AS lag_28,
        AVG(net_sales_qty) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS rolling_mean_7,
        AVG(net_sales_qty) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
            ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
        ) AS rolling_mean_28,
        STDDEV_SAMP(net_sales_qty) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
            ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
        ) AS rolling_std_28,
        MEDIAN(net_sales_qty) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
            ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
        ) AS rolling_median_28,
        LAG(avg_unit_price, 7) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
        ) AS avg_unit_price_lag_7,
        LAG(invoices_cnt, 7) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
        ) AS invoices_cnt_lag_7,
        LAG(customers_cnt, 7) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
        ) AS customers_cnt_lag_7,
        MAX(CASE WHEN net_sales_qty > 0 THEN sales_date END) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS previous_sale_date,
        MAX(CASE WHEN net_sales_qty > 0 THEN row_num END) OVER (
            PARTITION BY stock_code, market_id
            ORDER BY sales_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS previous_sale_row_num
    FROM ordered
)
SELECT
    sales_date,
    stock_code,
    description,
    market_id,
    sales_qty,
    avg_unit_price,
    revenue,
    invoices_cnt,
    customers_cnt,
    returns_qty,
    net_sales_qty,
    weekday,
    month,
    year,
    is_weekend,
    is_return_flag,
    is_price_missing,
    lag_7,
    lag_14,
    lag_28,
    rolling_mean_7,
    rolling_mean_28,
    rolling_std_28,
    rolling_median_28,
    avg_unit_price_lag_7,
    avg_unit_price - avg_unit_price_lag_7 AS price_change_abs,
    CASE
        WHEN avg_unit_price_lag_7 IS NULL OR avg_unit_price_lag_7 = 0 THEN NULL
        ELSE (avg_unit_price - avg_unit_price_lag_7) / avg_unit_price_lag_7
    END AS price_change_pct,
    invoices_cnt_lag_7,
    customers_cnt_lag_7,
    DATE_DIFF('day', previous_sale_date, sales_date) AS days_since_last_sale,
    CASE
        WHEN previous_sale_row_num IS NULL THEN row_num - 1
        ELSE row_num - previous_sale_row_num - 1
    END AS zero_sales_streak
FROM history;
