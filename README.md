

# Step 1: Install Postgres in Kubernetes with Kubegres Operator



Note
Manually Create a DB after installing Postgres

```
 kubectl  exec -it mypostgres-1-0 /bin/sh
 psql -U postgres
 <password>
 create database metadata;
 
 \list

 \c metadata (conenct to metadata DB)

 \dt (list the tables - After Step 2.1)
 ```

Get the EP 1p to give in the connection string in hive/metastore-cfg.yaml

```
kubectl get ep 

mypostgres               10.244.0.78:5432                    9h
mypostgres-replica       10.244.0.80:5432,10.244.0.82:5432   9h
```

```
            <property>
                <name>javax.jdo.option.ConnectionURL</name>
                <value>jdbc:postgresql://10.244.0.78:5432/metadata?allowPublicKeyRetrieval=true&amp;useSSL=false&amp;serverTimezone=UTC</value>
            </property>
```


# Step 2: Install Hive Metadata Standalone


## Step 2.1

Run the hive/hive-initschema.yaml Job to intialise the schema in the Postgre table

Create the relevant secrets

```
kubectl create secret generic my-s3-keys --from-literal=access-key=’minio’ --from-literal=secret-key=’minio123’
```

Install the hive metdata server 

```
kubectl apply -f  hive/hive-meta-store-standalone
```
