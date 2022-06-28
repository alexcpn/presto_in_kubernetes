from sqlalchemy import create_engine # Import the SQLAlchemy module
from sqlalchemy.schema import Table, MetaData 
from sqlalchemy.sql.expression import select, text
import pandas as pd

# Port forward the trino service first
# kubectl   port-forward svc/trino 8080 

engine = create_engine('trino://root@localhost:8080/hive')
connection = engine.connect()

# Using SQLAlchemy  

# Try to  create a table and Query it

create_schema = "CREATE SCHEMA  IF NOT EXISTS  hive.tpcds2"
create_table ="CREATE TABLE IF NOT EXISTS hive.tpcds2.store_sales AS SELECT * FROM tpcds.tiny.store_sales"
select_query = "SELECT * FROM tpcds2.store_sales"

proxy = connection.execution_options(stream_results=False).execute(create_schema)
proxy = connection.execution_options(stream_results=False).execute(create_table)
proxy = connection.execution_options(stream_results=True).execute(select_query)
rows = proxy.fetchmany(10)
for row in rows:
    print(row)

# Query with more data and write to a Pandas dataframe

query = "select *from nyc_in_parquet.tlc_yellow_trip_2022"
proxy = connection.execution_options(stream_results=True).execute(query)

# We can use the proxy to get the data in chunks
rows = proxy.fetchmany(10000)
df = pd.DataFrame(rows)
print(df.shape)

# However for big training data we may run out of memory
i =0
while 'batch not empty':  # equivalent of 'while True', but clearer
    batch = proxy.fetchmany(100000)  # 100,000 rows at a time
    if not batch:
        break
    df = pd.concat([df, pd.DataFrame.from_records(batch)])
    print(df.shape)
    i += 1
    if i > 1:
        print("Breaking out due to memory overload")  
        break

print(df.shape)
print(df.head)

# Testing a more complex query

aggregate_query ="""
select t.range, count(*) as "Number of Occurrence", ROUND(AVG(fare_amount),2) as "Avg",
  ROUND(MAX(fare_amount),2) as "Max" ,ROUND(MIN(fare_amount),2) as "Min" 
from (
  select 
   case 
      when trip_distance between  0 and  9 then ' 0-9 '
      when trip_distance between 10 and 19 then '10-19'
      when trip_distance between 20 and 29 then '20-29'
      when trip_distance between 30 and 39 then '30-39'
      else '> 39' 
   end as range ,fare_amount 
  from nyc_in_parquet.tlc_yellow_trip_2022) t
  where fare_amount > 1 and fare_amount < 401092
group by t.range
"""

proxy = connection.execution_options(stream_results=False).execute(aggregate_query)

rows = proxy.fetchall()
print("-------Aggregate query--------")
print(rows)


proxy.close()


