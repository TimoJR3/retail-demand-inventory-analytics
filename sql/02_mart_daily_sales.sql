-- Дневная витрина спроса по товару и стране.

CREATE OR REPLACE VIEW mart_daily_sales AS
SELECT
    date,
    stock_code,
    country,
    SUM(quantity) AS sales,
    SUM(revenue) AS revenue,
    AVG(unit_price) AS avg_unit_price,
    COUNT(DISTINCT invoice) AS invoices,
    COUNT(DISTINCT customer_id) AS customers
FROM transactions_clean
GROUP BY
    date,
    stock_code,
    country;

CREATE OR REPLACE VIEW mart_sku_summary AS
SELECT
    stock_code,
    country,
    SUM(sales) AS total_sales,
    SUM(revenue) AS total_revenue,
    AVG(sales) AS mean_daily_sales,
    STDDEV_SAMP(sales) AS std_daily_sales,
    COUNT(DISTINCT date) AS active_days
FROM mart_daily_sales
GROUP BY
    stock_code,
    country;

