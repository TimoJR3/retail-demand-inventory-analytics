-- Логическая схема аналитического слоя для транзакций онлайн-ритейла.
-- Сырые файлы не хранятся в репозитории. Данные загружаются вручную в data/raw/,
-- затем приводятся к единому формату в ноутбуке загрузки.

-- Календарный справочник. Нужен для группировки спроса по дням, неделям,
-- месяцам и выходным.
CREATE TABLE IF NOT EXISTS dim_date (
    sales_date DATE PRIMARY KEY,
    weekday INTEGER,
    month INTEGER,
    year INTEGER,
    is_weekend BOOLEAN
);

-- Справочник товаров. Описание может меняться в источнике, поэтому в витрине
-- используется последнее или наиболее частое описание на уровне stock_code.
CREATE TABLE IF NOT EXISTS dim_product (
    stock_code VARCHAR PRIMARY KEY,
    description VARCHAR
);

-- Справочник рынков. В текущем проекте market_id строится из Country.
CREATE TABLE IF NOT EXISTS dim_market (
    market_id VARCHAR PRIMARY KEY,
    country VARCHAR
);

-- Факт транзакций после нормализации названий колонок.
-- Возвраты и отмененные счета не удаляются: они помечаются флагом is_return_flag.
CREATE TABLE IF NOT EXISTS fct_transactions (
    invoice VARCHAR,
    stock_code VARCHAR,
    description VARCHAR,
    quantity DOUBLE,
    invoice_date TIMESTAMP,
    sales_date DATE,
    unit_price DOUBLE,
    customer_id VARCHAR,
    country VARCHAR,
    market_id VARCHAR,
    is_return_flag BOOLEAN,
    is_price_missing BOOLEAN,
    is_price_invalid BOOLEAN,
    revenue DOUBLE
);

-- Итоговая дневная витрина: одна строка = sales_date x stock_code x market_id.
CREATE TABLE IF NOT EXISTS mart_daily_sales (
    sales_date DATE,
    stock_code VARCHAR,
    description VARCHAR,
    market_id VARCHAR,
    sales_qty DOUBLE,
    avg_unit_price DOUBLE,
    revenue DOUBLE,
    invoices_cnt INTEGER,
    customers_cnt INTEGER,
    returns_qty DOUBLE,
    net_sales_qty DOUBLE,
    weekday INTEGER,
    month INTEGER,
    year INTEGER,
    is_weekend BOOLEAN,
    is_return_flag BOOLEAN,
    is_price_missing BOOLEAN
);
