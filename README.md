

Adapted from https://github.com/joshuarobinson/trino-on-k8s

and from https://joshua-robinson.medium.com/presto-powered-s3-data-warehouse-on-kubernetes-aea89d2f40e8


Main changes - Kind cluster, Mino S3, Updated Trino and changes for that, Updated Hive standanlone Docker, Postgres Database

# Step 0: Install Kind cluster if you dont have any other

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

 \c metadata (conenct to metadata DB)

 \dt (list the tables - After Step 2.1)



Get the EP  of Postgres

```
kubectl get ep 

mypostgres               10.244.0.78:5432                    9h
mypostgres-replica       10.244.0.80:5432,10.244.0.82:5432   9h
```

Update it in connection string
in `hive/metastore-cfg.yaml` and `hive/hive-initschema.yaml`



# Step 2: Install Hive Metadata Standalone


## Step 2.1

Run the hive/hive-initschema.yaml Job to intialise the schema in the Postgre table

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


Create the S3 secrets for Hive

```
kubectl create secret generic my-s3-keys --from-literal=access-key=’minio’ --from-literal=secret-key=’minio123’
```

Get the Mino/S3 EP

```
kubectl get ep  

alex@pop-os:~/coding/preso_hive$ kubectl get ep
NAME                      ENDPOINTS                                                      AGE
kubernetes                172.18.0.3:6443                                                29h
metastore                 10.244.1.37:9083                                               139m
mino-test-minio           10.244.1.11:9000,10.244.1.4:9000,10.244.1.8:9000 + 1 more...   24h
mino-test-minio-console   10.244.1.11:9001,10.244.1.4:9001,10.244.1.8:9001 + 1 more...   24h
mino-test-minio-svc       10.244.1.11:9000,10.244.1.4:9000,10.244.1.8:9000 + 1 more...   24h
mypostgres                10.244.1.5:5432                                                29h
mypostgres-replica        10.244.1.6:5432,10.244.1.7:5432                                29h
trino                     10.244.1.42:8080                                               3h43m
```

Update in `hive\metastroe-cfg.yaml` for S3

The following properties using Endpoints or Ingress for S3 and Postgres

```
<name>fs.s3a.endpoint</name>
<value>http://10.244.1.11:9001</value>
```                

Install the hive metdata server 

```
kubectl apply -f   hive/metastore-cfg.yaml
kubectl apply -f  hive/hive-meta-store-standalone.yaml
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


Acess Trino CLI


Give the EP of trino in the server argument below

```
kubectl exec -it trino-cli /bin/bash 
/bin/trino --server 10.244.1.115:8080 --catalog hive --schema default
```

Try to create a schema using S3

We are using the built in test datastrore `tpcds` to create load ;

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


Custom tables and queries next

```
CREATE SCHEMA hive.test WITH (location ='s3a://test/test4');

CREATE TABLE IF NOT EXISTS test.store (
  orderkey bigint,
  orderstatus varchar,
  totalprice double,
  orderdate date
)
WITH (format = 'ORC');
```

## Handy commands

After pod restarts the Endpoints that we gave change - so we need to change the dependent services endpoints too

```
kubectl apply -f hive/metastore-cfg.yaml && kubectl delete -f hive/hive-meta-store-standalone.yaml  && kubectl create -f hive/hive-meta-store-standalone.yaml
kubectl get ep | grep meta (update in trino_cfg.yaml)

kubectl apply -f trino/trino_cfg.yaml && kubectl delete -f trino/trino.yaml && kubectl create -f trino/trino.yaml
kubectl get ep | grep trino (update in psql)

kubectl   port-forward svc/trino 8080 
kubectl port-forward svc/mino-test-minio-console 9001
```


