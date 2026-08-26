WITH discrepancy_check AS (
    SELECT COUNT(*) AS discrepancy_count
    FROM public_test.dm_settlement_report_actual a
    FULL JOIN public_test.dm_settlement_report_expected e
        ON a.restaurant_id = e.restaurant_id 
        AND a.settlement_year = e.settlement_year 
        AND a.settlement_month = e.settlement_month
    WHERE 
        a.restaurant_id IS NULL 
        OR e.restaurant_id IS NULL
        OR a.restaurant_name <> e.restaurant_name
        OR a.orders_count <> e.orders_count
        OR a.orders_total_sum <> e.orders_total_sum
        OR a.orders_bonus_payment_sum <> e.orders_bonus_payment_sum
        OR a.orders_bonus_granted_sum <> e.orders_bonus_granted_sum
        OR a.order_processing_fee <> e.order_processing_fee
        OR a.restaurant_reward_sum <> e.restaurant_reward_sum
)
SELECT 
    CURRENT_TIMESTAMP AS test_date_time,
    'test_01' AS test_name,
    CASE 
        WHEN discrepancy_count = 0 THEN TRUE
        ELSE FALSE
    END AS test_result
FROM discrepancy_check;