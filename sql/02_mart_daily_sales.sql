-- Сборка дневной витрины спроса.
-- Одна строка = sales_date x stock_code x market_id.
-- Возвраты и отмененные счета не удаляются: они участвуют в returns_qty
-- и уменьшают net_sales_qty, который используется как целевая величина прогноза.

CREATE OR REPLACE TABLE mart_daily_sales AS
WITH prepared AS (
    SELECT
        CAST(invoice AS VARCHAR) AS invoice,
        CAST(stock_code AS VARCHAR) AS stock_code,
        TRIM(CAST(description AS VARCHAR)) AS description,
        CAST(quantity AS DOUBLE) AS quantity,
        CAST(invoice_date AS TIMESTAMP) AS invoice_date,
        CAST(invoice_date AS DATE) AS sales_date,
        CAST(unit_price AS DOUBLE) AS unit_price,
        CAST(customer_id AS VARCHAR) AS customer_id,
        TRIM(CAST(country AS VARCHAR)) AS market_id,
        CASE
            WHEN STARTS_WITH(CAST(invoice AS VARCHAR), 'C') OR CAST(quantity AS DOUBLE) < 0
            THEN TRUE
            ELSE FALSE
        END AS is_return_flag,
        CASE
            WHEN unit_price IS NULL
            THEN TRUE
            ELSE FALSE
        END AS is_price_missing,
        CASE
            WHEN unit_price IS NULL OR CAST(unit_price AS DOUBLE) <= 0
            THEN TRUE
            ELSE FALSE
        END AS is_price_invalid,
        CAST(quantity AS DOUBLE) * CAST(unit_price AS DOUBLE) AS revenue
    FROM fct_transactions
),
aggregated AS (
    SELECT
        sales_date,
        stock_code,
        ANY_VALUE(description) AS description,
        market_id,
        SUM(CASE WHEN NOT is_return_flag THEN quantity ELSE 0 END) AS sales_qty,
        AVG(CASE WHEN NOT is_price_invalid THEN unit_price END) AS avg_unit_price,
        SUM(revenue) AS revenue,
        COUNT(DISTINCT invoice) AS invoices_cnt,
        COUNT(DISTINCT customer_id) AS customers_cnt,
        ABS(SUM(CASE WHEN is_return_flag THEN quantity ELSE 0 END)) AS returns_qty,
        SUM(quantity) AS net_sales_qty,
        MAX(CASE WHEN is_return_flag THEN TRUE ELSE FALSE END) AS is_return_flag,
        MAX(CASE WHEN is_price_missing THEN TRUE ELSE FALSE END) AS is_price_missing
    FROM prepared
    WHERE sales_date IS NOT NULL
      AND stock_code IS NOT NULL
      AND market_id IS NOT NULL
    GROUP BY
        sales_date,
        stock_code,
        market_id
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
    EXTRACT('dow' FROM sales_date) AS weekday,
    EXTRACT('month' FROM sales_date) AS month,
    EXTRACT('year' FROM sales_date) AS year,
    CASE WHEN EXTRACT('dow' FROM sales_date) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,
    is_return_flag,
    is_price_missing
FROM aggregated;
