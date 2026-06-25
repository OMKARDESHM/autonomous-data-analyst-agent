INSERT INTO products(product_name, category, unit_price)

VALUES

('Laptop','Electronics',800),

('Mouse','Electronics',25),

('Keyboard','Electronics',50),

('Desk','Furniture',300),

('Chair','Furniture',180);

INSERT INTO regions(region_name,state,country)

VALUES

('Nagpur','Maharashtra','India'),

('Mumbai','Maharashtra','India'),

('Delhi','Delhi','India'),

('Bangalore','Karnataka','India'),

('Hyderabad','Telangana','India');

INSERT INTO time_periods

(sale_date,month,quarter,year)

VALUES

('2025-01-15',1,1,2025),

('2025-02-10',2,1,2025),

('2025-03-11',3,1,2025),

('2025-04-18',4,2,2025),

('2025-05-22',5,2,2025);

INSERT INTO sales

(product_id,region_id,time_id,quantity,revenue,profit)

VALUES

(1,1,1,12,9600,2200),

(2,2,2,120,3000,900),

(3,3,3,90,4500,1100),

(4,4,4,18,5400,1600),

(5,5,5,24,4320,1400),

(1,2,3,20,16000,4800),

(2,1,5,250,6250,1800),

(4,3,2,10,3000,850),

(5,4,4,15,2700,600);

