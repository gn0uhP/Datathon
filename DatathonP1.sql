--Q1
WITH OrderDates AS (
    SELECT 
        customer_id, 
        order_date,
        LAG(order_date) OVER(PARTITION BY customer_id ORDER BY order_date) AS prev_order_date
    FROM orders
),
Gaps AS (
    SELECT DATEDIFF(day, prev_order_date, order_date) AS gap_days
    FROM OrderDates
    WHERE prev_order_date IS NOT NULL
)
SELECT DISTINCT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY gap_days) OVER() AS Median_Gap_Days
FROM Gaps;

--Q2:
SELECT TOP 1 
    segment, 
    AVG((price - cogs) / price) AS avg_gross_margin
FROM products
GROUP BY segment
ORDER BY avg_gross_margin DESC;

--Q3:
SELECT TOP 1 
    r.return_reason, 
    COUNT(*) AS total_returns
FROM returns r
JOIN products p ON r.product_id = p.product_id
WHERE p.category = 'Streetwear'
GROUP BY r.return_reason
ORDER BY total_returns DESC;

--Q4:
SELECT TOP 1 
    traffic_source, 
    AVG(bounce_rate) AS avg_bounce_rate
FROM web_traffic
GROUP BY traffic_source
ORDER BY avg_bounce_rate ASC;

--Q5:
SELECT 
    (COUNT(CASE WHEN promo_id IS NOT NULL THEN 1 END) * 100.0) / COUNT(*) AS promo_percentage
FROM order_items;

--Q6:
SELECT TOP 1 
    c.age_group, 
    CAST(COUNT(o.order_id) AS FLOAT) / COUNT(DISTINCT c.customer_id) AS avg_orders_per_customer
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE c.age_group IS NOT NULL
GROUP BY c.age_group
ORDER BY avg_orders_per_customer DESC;

--Q7:
SELECT TOP 1 
    g.region, 
    SUM(p.payment_value) AS total_revenue
FROM orders o
JOIN geography g ON o.zip = g.zip
JOIN payments p ON o.order_id = p.order_id
GROUP BY g.region
ORDER BY total_revenue DESC;

--Q8:
SELECT TOP 1 
    payment_method, 
    COUNT(*) AS count_cancelled
FROM orders
WHERE order_status = 'cancelled'
GROUP BY payment_method
ORDER BY count_cancelled DESC;

--Q9:
WITH OrderedItems AS (
    SELECT p.size, COUNT(*) AS total_ordered
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    WHERE p.size IN ('S', 'M', 'L', 'XL')
    GROUP BY p.size
),
ReturnedItems AS (
    SELECT p.size, COUNT(*) AS total_returned
    FROM returns r
    JOIN products p ON r.product_id = p.product_id
    WHERE p.size IN ('S', 'M', 'L', 'XL')
    GROUP BY p.size
)
SELECT TOP 1 
    o.size, 
    CAST(ISNULL(r.total_returned, 0) AS FLOAT) / o.total_ordered AS return_rate
FROM OrderedItems o
LEFT JOIN ReturnedItems r ON o.size = r.size
ORDER BY return_rate DESC;

--Q10:
SELECT TOP 1 
    installments, 
    AVG(payment_value) AS avg_payment_value
FROM payments
GROUP BY installments
ORDER BY avg_payment_value DESC;