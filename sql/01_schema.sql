-- Схема исходной таблицы после нормализации названий колонок.
-- Сырые файлы не хранятся в репозитории. Таблица может быть создана в DuckDB
-- после ручной загрузки Excel/CSV через Python-ноутбук.

CREATE TABLE IF NOT EXISTS transactions_raw (
    invoice VARCHAR,
    stock_code VARCHAR,
    description VARCHAR,
    quantity DOUBLE,
    invoice_date TIMESTAMP,
    unit_price DOUBLE,
    customer_id VARCHAR,
    country VARCHAR
);

CREATE OR REPLACE VIEW transactions_clean AS
SELECT
    CAST(invoice AS VARCHAR) AS invoice,
    CAST(stock_code AS VARCHAR) AS stock_code,
    TRIM(CAST(description AS VARCHAR)) AS description,
    CAST(quantity AS DOUBLE) AS quantity,
    CAST(invoice_date AS TIMESTAMP) AS invoice_date,
    CAST(unit_price AS DOUBLE) AS unit_price,
    CAST(customer_id AS VARCHAR) AS customer_id,
    TRIM(CAST(country AS VARCHAR)) AS country,
    CAST(invoice_date AS DATE) AS date,
    CAST(quantity AS DOUBLE) * CAST(unit_price AS DOUBLE) AS revenue
FROM transactions_raw
WHERE invoice_date IS NOT NULL
  AND stock_code IS NOT NULL
  AND quantity > 0
  AND unit_price > 0
  AND NOT STARTS_WITH(CAST(invoice AS VARCHAR), 'C');

