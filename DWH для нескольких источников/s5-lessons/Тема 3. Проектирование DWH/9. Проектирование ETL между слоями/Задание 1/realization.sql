INSERT INTO cdm.dm_settlement_report (
    restaurant_id,
    restaurant_name,
    settlement_date,
    orders_count,
    orders_total_sum,
    orders_bonus_payment_sum,
    orders_bonus_granted_sum,
    order_processing_fee,
    restaurant_reward_sum
)
SELECT
    r.id::varchar(255),
    r.restaurant_name,
    t.date,
    COUNT(DISTINCT fct.order_id),
    COALESCE(SUM(fct.total_sum), 0),
    COALESCE(SUM(fct.bonus_payment), 0),
    COALESCE(SUM(fct.bonus_grant), 0),
    (COALESCE(SUM(fct.total_sum), 0) * 0.25)::numeric(14,2),
    (
        COALESCE(SUM(fct.total_sum), 0)
        - COALESCE(SUM(fct.bonus_payment), 0)
        - (COALESCE(SUM(fct.total_sum), 0) * 0.25)::numeric(14,2)
    )::numeric(14,2)
FROM dds.fct_product_sales fct
LEFT JOIN dds.dm_orders o ON fct.order_id = o.id
LEFT JOIN dds.dm_restaurants r ON r.id = o.restaurant_id
LEFT JOIN dds.dm_timestamps t ON t.id = o.timestamp_id
WHERE o.order_status = 'CLOSED'
GROUP BY r.id, r.restaurant_name, t.date
ON CONFLICT (restaurant_id, settlement_date) DO UPDATE SET
    restaurant_name = EXCLUDED.restaurant_name,
    orders_count = EXCLUDED.orders_count,
    orders_total_sum = EXCLUDED.orders_total_sum,
    orders_bonus_payment_sum = EXCLUDED.orders_bonus_payment_sum,
    orders_bonus_granted_sum = EXCLUDED.orders_bonus_granted_sum,
    order_processing_fee = EXCLUDED.order_processing_fee,
    restaurant_reward_sum = EXCLUDED.restaurant_reward_sum;
