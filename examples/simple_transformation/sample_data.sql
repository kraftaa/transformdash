-- Sample data for TransformDash simple transformation example

-- Create customers table
CREATE TABLE IF NOT EXISTS raw_customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE IF NOT EXISTS raw_orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES raw_customers(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending'
);

-- Insert sample customers
INSERT INTO raw_customers (email, name, created_at) VALUES
('alice@example.com', 'Alice Smith', '2024-01-15 10:00:00'),
('bob@example.com', 'Bob Jones', '2024-01-20 11:30:00'),
('carol@example.com', 'Carol White', '2024-02-01 09:15:00'),
('david@example.com', 'David Brown', '2024-02-10 14:20:00'),
('eve@example.com', 'Eve Davis', '2024-03-05 16:45:00');

-- Insert sample orders
INSERT INTO raw_orders (customer_id, order_date, total_amount, status) VALUES
(1, '2024-01-16 12:00:00', 150.00, 'completed'),
(1, '2024-02-20 15:30:00', 200.50, 'completed'),
(2, '2024-01-25 10:15:00', 75.25, 'completed'),
(2, '2024-03-01 11:00:00', 120.00, 'pending'),
(3, '2024-02-05 13:45:00', 300.75, 'completed'),
(3, '2024-03-10 16:20:00', 180.00, 'shipped'),
(4, '2024-02-15 09:30:00', 95.50, 'completed'),
(5, '2024-03-08 14:00:00', 450.25, 'completed');

SELECT 'Sample data loaded successfully!' AS status;
