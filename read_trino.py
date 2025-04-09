import trino
import pandas as pd

# Connect to Trino
conn = trino.dbapi.connect(
    host='localhost',
    port=8080,
    user='your_username',
    catalog='hive',
    schema='mydatabase',
)

# Query to fetch data
query = "SELECT title, description, issue_type FROM mytable"

# Execute query and load data into a DataFrame
df = pd.read_sql(query, conn)
print(df.head())