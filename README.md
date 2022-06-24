
# DataLakeHouse: Trino (PrestoSQL) with S3 in Kubernetes Baremetal
## Trino, HiveMetStore Standalone, MinoS3, Postgres DB in Kind cluster

Based and expanded  from https://github.com/joshuarobinson/trino-on-k8s
and from https://joshua-robinson.medium.com/presto-powered-s3-data-warehouse-on-kubernetes-aea89d2f40e8

Main changes - Kind cluster, Minio S3, Updated Trino and changes for that, Updated Hive standalone Dockerfile, Postgres Database


# What is a DataLakeHouse ?

This is a mouthful; I hope everyone has heard of DataWareHouse. That's old school now based on Hadoop and HDFS file system; which is hard to operate and maintain


The cool kid on the block is S3, and DataLake is data on S3.
DataLakeHouse is data on S3, but with a SQL Table and Schema kept for that and hence data that can be queried
# System Diagram

**Components**

- Trino - Is a Distributed SQL Engine
- Hive - We use only Hive Metadata Server Standalone here; This uses a DB (we use Postgres) to persist. This stores the Table structure
- S3 - This holds the data as S3 object; The meta-structure for this is stored and kept in Hive
- Parquet - The data in S3 is stored in Apache Parquet , binary compressed and columnar data format

![DataLake](https://i.imgur.com/Dg9jM61.png)

# Step 0: Install Kind cluster

Create a Kind Cluster, with memory limitation

```
kind create cluster --config /home/alex/coding/preso_hive/kind-cluster-config.yaml
```

Install Minio for S3

Via helm

```
https://github.com/minio/minio/tree/master/helm/minio
helm install mino-test -f mino/values.yaml  minio/minio
```

Create a bucket `test` from the UI

```
kubectl port-forward svc/mino-test-minio-console 9001
```

# Step 1: Install Postgres in Kubernetes with Kubegres Operator

Postgres in Kubernetes https://www.kubegres.io/

https://www.kubegres.io/doc/getting-started.html

```
kubectl apply -f https://raw.githubusercontent.com/reactive-tech/kubegres/v1.15/kubegres.yaml
kubectl apply -f postgres/postgres-secret.yaml
kubectl apply -f postgres/kubegres-porstrescluster.yaml
```

```
kubectl get pods
NAME             READY   STATUS    RESTARTS   AGE
mypostgres-1-0   1/1     Running   0          22m
mypostgres-2-0   1/1     Running   0          22m
mypostgres-3-0   1/1     Running   0          22m
```

Manually Create a DB after installing Postgres


```
 kubectl  exec -it mypostgres-1-0 /bin/sh
 psql -U postgres
 <password from the secret>

postgres=# create database metadata;
CREATE DATABASE
```
Check if the DB is cerated

```
postgres=# \list
                                 List of databases
   Name    |  Owner   | Encoding |  Collate   |   Ctype    |   Access privileges   
-----------+----------+----------+------------+------------+-----------------------
 metadata  | postgres | UTF8     | en_US.utf8 | en_US.utf8 | 
 postgres  | postgres | UTF8     | en_US.utf8 | en_US.utf8 | 
 template0 | postgres | UTF8     | en_US.utf8 | en_US.utf8 | =c/postgres          +
           |          |          |            |            | postgres=CTc/postgres
 template1 | postgres | UTF8     | en_US.utf8 | en_US.utf8 | =c/postgres          +
           |          |          |            |            | postgres=CTc/postgres

```

Other commands

 \c metadata (connect to metadata DB)

 \dt (list the tables - After Step 2.1)

Get the Postgres Service

Update it in connection string
in `hive/metastore-cfg.yaml` and `hive/hive-initschema.yaml`

# Step 2: Install Hive Metadata Standalone

## Step 2.1

Run the `hive/hive-initschema.yaml` Job to initialize the schema in the Postgres table

```
kubectl apply -f hive/hive-initschema.yaml
```
and verify if the tables are created properly

```
 kubectl  exec -it mypostgres-1-0 /bin/sh
 psql -U postgres 
 postgresSuperUserPsw

\list
\c metadata
\dt
\q

To drop table in use

SELECT                  
    pg_terminate_backend(pid) 
FROM 
    pg_stat_activity ;

drop database metadata;
````
## Step 2.2

Create the S3 secrets for Hive

```
kubectl create secret generic my-s3-keys --from-literal=access-key=’minio’ --from-literal=secret-key=’minio123’
```

Get the Mino/S3 service

```
kubectl get svc
kubernetes                ClusterIP   10.96.0.1       <none>        443/TCP    7d
metastore                 ClusterIP   10.96.189.200   <none>        9083/TCP   4m8s
mino-test-minio           ClusterIP   10.96.149.113   <none>        9000/TCP   6d18h
mino-test-minio-console   ClusterIP   10.96.236.45    <none>        9001/TCP   6d18h
mino-test-minio-svc       ClusterIP   None            <none>        9000/TCP   6d18h
mypostgres                ClusterIP   None            <none>        5432/TCP   29m
mypostgres-replica        ClusterIP   None            <none>        5432/TCP   6d23h
trino                     ClusterIP   10.96.249.19    <none>        8080/TCP   63s                                       3h43m
```

Update in `hive\metastroe-cfg.yaml` for S3 and Postgres

Note especially the below property. We are pointing the `metastore.warehouse.dir` to the S3 location; All Schemas and tables will hereby get created in S3.

```
   <property>
      <name>metastore.warehouse.dir</name>
      <value>s3a://test/warehouse</value>
   </property>
```            

**NOTE** Sometimes giving the service in Kindcluster gave me read timeouts from Hive. So I changed that to Endpoints (that is IP's) in `metastore-cfg.yaml`. This means that everytime the Kind cluster restarts the Endpoints have to reset and hive reployed for now. Need to check this later

## Step 2.3

First build the HiveMetastore Standalone

```
docker build -t hivemetastore:3.1.3.5 -f hive/Dockerfile ./hive
docker tag hivemetastore:3.1.3.5 alexcpn/hivemetastore:3.1.3.5
docker push alexcpn/hivemetastore:3.1.3.5
 ```

## Step 2.4

Install the hive metdata server 

```
kubectl apply -f hive/metastore-cfg.yaml && kubectl delete -f hive/hive-meta-store-standalone.yaml  && kubectl create -f hive/hive-meta-store-standalone.yaml
```


# Step 4. Install Trino (PrestoSQL)

Configure the Postgres,S3, and metastrore EP first in `trino\trino_cfg.yaml`

```
kubectl apply -f trino/trino_cfg.yaml
kubectl apply -f trino.yaml
```

Port forward to see the UI

```
kubectl   port-forward svc/trino 8080  &
```

# Part 2

Create a table in S3 via Trino

## Access Trino CLI

Give the Service of trino in the server argument below

```
kubectl exec -it trino-cli /bin/bash 
/bin/trino --server trino:8080 --catalog hive --schema default
```

Try to create a schema using S3

We are using the built in test datastrore `tpcds` to create tables and it will be auto-populated;

```
show schemas from tpcds;
show tables  from tpcds.tiny;
```

```
trino:default> CREATE SCHEMA hive.tpcds WITH (location = 's3a://test/warehouse/tpcds/');
trino:default> CREATE TABLE tpcds.store_sales AS SELECT * FROM tpcds.tiny.store_sales;
CREATE TABLE: 120527 rows

Query 20220617_125702_00006_sqada, FINISHED, 3 nodes
Splits: 14 total, 14 done (100.00%)
20.24 [121K rows, 0B] [5.95K rows/s, 0B/s]

```

You can see that in S3 the files are written

![filesins3](https://i.imgur.com/aEe7GzV.png)

```
trino:default> select count(*) from tpcds.store_sales;
 _col0  
--------
 120527 
(1 row)
````

You can see the queries getting executed via the Trino UI

![trino_ui](https://i.imgur.com/HFXqMGc.png)

## Handy commands

```
kubectl apply -f hive/metastore-cfg.yaml && kubectl delete -f hive/hive-meta-store-standalone.yaml  && kubectl create -f hive/hive-meta-store-standalone.yaml

kubectl apply -f trino/trino_cfg.yaml && kubectl delete -f trino/trino.yaml && kubectl create -f trino/trino.yaml

kubectl   port-forward svc/trino 8080 
kubectl port-forward svc/mino-test-minio-console 9001

kubectl exec -it trino-cli /bin/bash 
/bin/trino --server trino:8080 --catalog hive --schema default
```

## Installing  Redash

From https://github.com/getredash/contrib-helm-chart

## Optional: Install Redash 

Redash is a GUI to execute  SQL queries using various Data sources. Trino is also supported. And it can be used to analyze data

Minor changes below for proper installation
```
helm repo add redash https://getredash.github.io/contrib-helm-chart/

Get the template instead of directly installing

helm template  myredash -f redash/my-values.yaml  redash/redash >> redash/deployment.yaml

and updated the following to latest,as Image pull error was there in older; Also made the passwords in my-value smaller as some erros 
were coming

- name: myredash-postgresql
 image: docker.io/bitnami/postgresql:14.4.0-debian-11-r1
- name: redis
 image: docker.io/bitnami/redis:6.0.16-debian-11-r7
```
Once installed - Port forward to see the GUI


```
kubectl port-forward svc/myredash 8081:80
```

You can configure the Trino data source like below; and use redash for query execution and visualization

![redash_config](https://i.imgur.com/2OS7zdz.png)

Query Execution and Visualization

![redash_visalization](https://i.imgur.com/pIRqHkp.png)

Further tests are described here [More tests, Transactions, Update, CSV etc](testqueries.md)
