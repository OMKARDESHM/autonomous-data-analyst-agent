DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS regions;
DROP TABLE IF EXISTS time_periods;

CREATE TABLE products (

    product_id SERIAL PRIMARY KEY,

    product_name VARCHAR(100),

    category VARCHAR(100),

    unit_price DECIMAL(10,2)

);

CREATE TABLE regions (

    region_id SERIAL PRIMARY KEY,

    region_name VARCHAR(100),

    state VARCHAR(100),

    country VARCHAR(100)

);

CREATE TABLE time_periods (

    time_id SERIAL PRIMARY KEY,

    sale_date DATE,

    month INTEGER,

    quarter INTEGER,

    year INTEGER

);

CREATE TABLE sales (

    sale_id SERIAL PRIMARY KEY,

    product_id INTEGER REFERENCES products(product_id),

    region_id INTEGER REFERENCES regions(region_id),

    time_id INTEGER REFERENCES time_periods(time_id),

    quantity INTEGER,

    revenue DECIMAL(12,2),

    profit DECIMAL(12,2)

);