-- Сценарные proxy-метрики inventory risk.
-- В исходных данных нет фактических складских остатков, поэтому ниже нет вывода
-- "товар точно закончится" или "товара точно слишком много". Мы показываем
-- сценарный риск на основе факта, прогноза и простого допущения о доступном запасе.

-- Ожидаемый входной слой: forecast_vs_actual_sample
-- Поля: sales_date, stock_code, market_id, net_sales_qty, forecast_net_sales_qty.
-- Итоговый grain view inventory_metrics: stock_code x market_id.
-- net_sales_qty может быть отрицательным из-за возвратов, поэтому для политики
-- запасов спрос явно ограничивается снизу нулем.

CREATE OR REPLACE VIEW inventory_metrics AS
WITH prepared AS (
    SELECT
        CAST(sales_date AS DATE) AS sales_date,
        CAST(stock_code AS VARCHAR) AS stock_code,
        CAST(market_id AS VARCHAR) AS market_id,
        CAST(net_sales_qty AS DOUBLE) AS actual_sales,
        CAST(forecast_net_sales_qty AS DOUBLE) AS forecast_sales,
        GREATEST(CAST(net_sales_qty AS DOUBLE), 0) AS actual_demand_for_policy,
        GREATEST(CAST(forecast_net_sales_qty AS DOUBLE), 0) AS forecast_demand_for_policy,
        7 AS lead_time_days,
        1.65 AS z_score
    FROM forecast_vs_actual_sample
    WHERE sales_date IS NOT NULL
      AND stock_code IS NOT NULL
      AND market_id IS NOT NULL
      AND net_sales_qty IS NOT NULL
      AND forecast_net_sales_qty IS NOT NULL
),
row_flags AS (
    SELECT
        *,
        ABS(actual_demand_for_policy - forecast_demand_for_policy) AS abs_error,
        forecast_demand_for_policy - actual_demand_for_policy AS signed_error,
        CASE
            WHEN actual_demand_for_policy > forecast_demand_for_policy
            THEN TRUE
            ELSE FALSE
        END AS stockout_risk_flag,
        CASE
            WHEN forecast_demand_for_policy > actual_demand_for_policy
            THEN TRUE
            ELSE FALSE
        END AS overstock_risk_flag
    FROM prepared
),
aggregated AS (
    SELECT
        stock_code,
        market_id,
        AVG(actual_demand_for_policy) AS avg_daily_demand,
        COALESCE(STDDEV_SAMP(actual_demand_for_policy), 0) AS demand_std,
        CASE
            WHEN SUM(actual_demand_for_policy) = 0 AND SUM(abs_error) = 0 THEN 0
            WHEN SUM(actual_demand_for_policy) = 0 THEN 1
            ELSE SUM(abs_error) / SUM(actual_demand_for_policy)
        END AS forecast_error,
        CASE
            WHEN SUM(actual_demand_for_policy) = 0 AND SUM(signed_error) = 0 THEN 0
            WHEN SUM(actual_demand_for_policy) = 0 AND SUM(signed_error) > 0 THEN 1
            WHEN SUM(actual_demand_for_policy) = 0 AND SUM(signed_error) < 0 THEN -1
            ELSE SUM(signed_error) / SUM(actual_demand_for_policy)
        END AS forecast_bias,
        MAX(stockout_risk_flag) AS stockout_risk_flag,
        MAX(overstock_risk_flag) AS overstock_risk_flag,
        7 AS lead_time_days,
        1.65 AS z_score
    FROM row_flags
    GROUP BY
        stock_code,
        market_id
)
SELECT
    stock_code,
    market_id,
    avg_daily_demand,
    demand_std,
    forecast_error,
    forecast_bias,
    stockout_risk_flag,
    overstock_risk_flag,
    avg_daily_demand * lead_time_days
        + z_score * demand_std * SQRT(lead_time_days) AS suggested_reorder_point,
    z_score * demand_std * SQRT(lead_time_days) AS suggested_safety_stock
FROM aggregated;
