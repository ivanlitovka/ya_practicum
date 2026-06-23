--f_activity
DELETE FROM mart.f_activity;
INSERT INTO mart.f_activity (activity_id, date_id, click_number)
SELECT 
    ual.action_id AS activity_id,
    dc.date_id AS date_id,
    COUNT(*) AS click_number
FROM stage.user_activity_log ual 
INNER JOIN mart.d_calendar dc ON ual.date_time = dc.fact_date
GROUP BY  ual.action_id, dc.date_id
ORDER BY dc.date_id, ual.action_id;

--f_daily_sales
DELETE FROM mart.f_daily_sales;

INSERT INTO mart.f_daily_sales  (date_id, item_id, customer_id , price , quantity , payment_amount)
SELECT
    dc.date_id AS date_id,
    uol.item_id AS item_id,
    uol.customer_id AS customer_id,
    AVG(CASE WHEN uol.quantity > 0 THEN uol.payment_amount / uol.quantity ELSE 0 END) AS price,
    SUM(uol.quantity) AS quantity,
    SUM(uol.payment_amount) AS payment_amount
FROM stage.user_order_log uol 
INNER JOIN mart.d_calendar dc ON uol.date_time = dc.fact_date
GROUP BY dc.date_id, uol.item_id, uol.customer_id
ORDER BY dc.date_id, uol.item_id, uol.customer_id;
