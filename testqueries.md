
# Test 1 : ALTER TABLE and Update

Summary - Fail

- 1. Create a table and alter the table or update the data

For altering the table or updating, you need to create a table that supports transactions

```
CREATE TABLE test4.employee (id int, name varchar, salary int)
WITH (
   format='ORC'
   );

INSERT INTO test4.employee VALUES
(1, 'Jerry', 5000),
(2, 'Tom',   8000),
(3, 'Kate',  6000);
```

Insert works; trying to alter the table

```
ALTER TABLE test4.employee ADD column description varchar;

update test4.employee  set description ='Employee Jerry description' where id=1;
Query 20220622_105039_00034_7tuyy failed: Hive update is only supported for ACID transactional tables
```

- 2. Creating a Table with ACID transactions support - Works

```
trino:default> CREATE TABLE test4.employee5 (id int, name varchar, salary int)
            -> WITH (
            ->    format='ORC',
            ->    transactional=true
            ->    );
CREATE TABLE
trino:default> ALTER TABLE test4.employee5 ADD column description varchar;
ADD COLUMN
```

- 3. Inserting into a table with transaction -Does not work now!

```
trino:default> INSERT INTO test4.employee5 VALUES
            -> (1, 'Jerry', 5000,  'test'),
            -> (2, 'Tom',   8000, 'test'),
            -> (3, 'Kate',  6000, 'test');
INSERT: 3 rows

Query 20220623_043713_00027_7tuyy, FAILED, 3 nodes
Splits: 8 total, 8 done (100.00%)
10.69 [0 rows, 0B] [0 rows/s, 0B/s]

Query 20220623_043713_00027_7tuyy failed: Invalid method name: 'alter_table_req'
```

Does not work - Bug raised - https://github.com/trinodb/trino/issues/12949

# Test 2: Load Training Data as CSV and Query with Presto

Followed - https://towardsdatascience.com/load-and-query-csv-file-in-s3-with-presto-b0d50bc773c9

Downloaded part of data from https://catalog.data.gov/dataset/2018-yellow-taxi-trip-data and uploaded to S3 (Mino bucket) in this particular location 

```
s3a://test/warehouse/nyc_text.db/tlc_yellow_trips_2018'
```
![csv upload location](https://i.imgur.com/rm7QYdT.png)

Note that the Path is where we will create the SCHEMA and table as next step

Create SCHEMA

```
CREATE SCHEMA nyc_text ;
```

Since we have give metadata store default path in S3, this will create DB in S3 at  `s3a://test/warehouse/nyc_text.db`

Create Table, the External_location aligns to the path where we uploaded the csv

```
CREATE TABLE nyc_text.tlc_yellow_trips_2018 (
    vendorid VARCHAR,
    tpep_pickup_datetime VARCHAR,
    tpep_dropoff_datetime VARCHAR,
    passenger_count VARCHAR,
    trip_distance VARCHAR,
    ratecodeid VARCHAR,
    store_and_fwd_flag VARCHAR,
    pulocationid VARCHAR,
    dolocationid VARCHAR,
    payment_type VARCHAR,
    fare_amount VARCHAR,
    extra VARCHAR,
    mta_tax VARCHAR,
    tip_amount VARCHAR,
    tolls_amount VARCHAR,
    improvement_surcharge VARCHAR,
    total_amount VARCHAR)
WITH (FORMAT = 'CSV',
    skip_header_line_count = 1,
    EXTERNAL_LOCATION = 's3a://test/warehouse/nyc_text.db/tlc_yellow_trips_2018')
;
```

Try to Query the data out- Works

 ```
 trino:default> select * from hive.nyc_text.tlc_yellow_trips_2018;
 vendorid |  tpep_pickup_datetime  | tpep_dropoff_datetime  | passenger_count | trip_distance | ratecodeid | store_and_fwd_flag | pulocationid | dolocationid | payment_type | >
----------+------------------------+------------------------+-----------------+---------------+------------+--------------------+--------------+--------------+--------------+->
 2        | 06/29/2018 02:38:33 PM | 06/29/2018 03:29:33 PM | 2               | 10.46         | 1          | N                  | 140          | 61           | 2            | >
 2        | 06/29/2018 02:05:23 PM | 06/29/2018 02:15:41 PM | 5               | 2.02          | 1          | N                  | 249          | 13           | 1            | >
 2        | 06/29/2018 02:20:52 PM | 06/29/2018 02:51:28 PM | 5               | 4.32          | 1          | N                  | 13           | 4            | 1            | >
```

Convert this to ORC or Parquet as each field in CSV is read as VARCHAR

```
CREATE SCHEMA hive.nyc_parq;

CREATE TABLE hive.nyc_parq.tlc_yellow_trips_2018
COMMENT '2018 Newyork City taxi data'
WITH (FORMAT = 'PARQUET')
AS
SELECT 
    cast(vendorid as INTEGER) as vendorid,
    date_parse(tpep_pickup_datetime, '%m/%d/%Y %h:%i:%s %p') as tpep_pickup_datetime,
    date_parse(tpep_dropoff_datetime, '%m/%d/%Y %h:%i:%s %p') as tpep_dropoff_datetime,
    cast(passenger_count as SMALLINT) as passenger_count,
    cast(trip_distance as DECIMAL(8, 2)) as trip_distance,
    cast(ratecodeid as INTEGER) as ratecodeid,
    cast(store_and_fwd_flag as CHAR(1)) as store_and_fwd_flag,
    cast(pulocationid as INTEGER) as pulocationid,
    cast(dolocationid as INTEGER) as dolocationid,
    cast(payment_type as SMALLINT) as payment_type,
    cast(fare_amount as DECIMAL(8, 2)) as fare_amount,
    cast(extra as DECIMAL(8, 2)) as extra,
    cast(mta_tax as DECIMAL(8, 2)) as mta_tax,
    cast(tip_amount as DECIMAL(8, 2)) as tip_amount,
    cast(tolls_amount as DECIMAL(8, 2)) as tolls_amount,
    cast(improvement_surcharge as DECIMAL(8, 2)) as improvement_surcharge,
    cast(total_amount as DECIMAL(8, 2)) as total_amount
FROM hive.nyc_text.tlc_yellow_trips_2018;
```

```
DESCRIBE nyc_parq.tlc_yellow_trips_2018;

The conversion is successful

trino:default> DESCRIBE nyc_parq.tlc_yellow_trips_2018;
        Column         |     Type     | Extra | Comment 
-----------------------+--------------+-------+---------
 vendorid              | integer      |       |         
 tpep_pickup_datetime  | timestamp(3) |       |         
 tpep_dropoff_datetime | timestamp(3) |       |         
 passenger_count       | smallint     |       |         
 trip_distance         | decimal(8,2) |       |         
 ratecodeid            | integer      |       |         
 store_and_fwd_flag    | char(1)      |       |         
 pulocationid          | integer      |       |         
 dolocationid          | integer      |       |         
 payment_type          | smallint     |       |         
 fare_amount           | decimal(8,2) |       |         
 extra                 | decimal(8,2) |       |         
 mta_tax               | decimal(8,2) |       |         
 tip_amount            | decimal(8,2) |       |         
 tolls_amount          | decimal(8,2) |       
 ```