-- Сценарные метрики запасов. Фактического остатка в источнике нет,
-- поэтому stock_on_hand задается отдельным сценарием в аналитическом слое.

CREATE OR REPLACE VIEW inventory_metrics_base AS
SELECT
    stock_code,
    country,
    AVG(sales) AS mean_daily_demand,
    COALESCE(STDDEV_SAMP(sales), 0) AS demand_std,
    7 AS lead_time_days,
    1.65 AS service_level_z,
    AVG(sales) * 7 AS lead_time_demand,
    1.65 * COALESCE(STDDEV_SAMP(sales), 0) * SQRT(7) AS safety_stock,
    AVG(sales) * 7 + 1.65 * COALESCE(STDDEV_SAMP(sales), 0) * SQRT(7) AS reorder_point
FROM mart_daily_sales
GROUP BY
    stock_code,
    country;

CREATE OR REPLACE VIEW inventory_risk_template AS
SELECT
    stock_code,
    country,
    mean_daily_demand,
    demand_std,
    lead_time_days,
    safety_stock,
    reorder_point,
    CAST(NULL AS DOUBLE) AS stock_on_hand,
    '[A]' AS stockout_risk_note,
    '[B]' AS overstock_risk_note
FROM inventory_metrics_base;

