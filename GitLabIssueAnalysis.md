
# DataLakeHouse: Trino (PrestoSQL) with S3 in Kubernetes Baremetal

## Trino, HiveMetStore Standalone, MinoS3, Postgres DB in Kind cluster

Based and expanded  from <https://github.com/joshuarobinson/trino-on-k8s>
and from <https://joshua-robinson.medium.com/presto-powered-s3-data-warehouse-on-kubernetes-aea89d2f40e8>

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
helm repo add minio https://charts.min.io/
helm install mino-test -f mino/values.yaml  minio/minio
```

Create a bucket `test` from the UI

```
kubectl port-forward svc/mino-test-minio-console 9001
```

Access via

<http://localhost:9001/login>

# Step 1: Install Postgres in Kubernetes with Kubegres Operator

Postgres in Kubernetes <https://www.kubegres.io/>

<https://www.kubegres.io/doc/getting-started.html>

```
kubectl apply -f https://raw.githubusercontent.com/reactive-tech/kubegres/v1.19/kubegres.yaml
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

```
kubectl get secrets
NAME                              TYPE                 DATA   AGE
mino-test-minio                   Opaque               2      6m24s
mypostgres-secret                 Opaque               2      43s
sh.helm.release.v1.mino-test.v1   helm.sh/release.v1   1      6m24s

kubectl get secret mypostgres-secret -o yaml
```

Manually Create a DB after installing Postgres

```
 kubectl  exec -it mypostgres-1-0 -- /bin/sh
 psql -U postgres
 <password from the secret> postgresSuperUserPsw

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
 kubectl  exec -it mypostgres-1-0 -- /bin/sh
 psql -U postgres 
 postgresSuperUserPsw

\list
\c metadata
\dt

                     List of relations
 Schema |             Name              | Type  |  Owner   
--------+-------------------------------+-------+----------
 public | BUCKETING_COLS                | table | postgres
 public | CDS                           | table | postgres
 public | COLUMNS_V2                    | table | postgres
 public | CTLGS                         | table | postgres
 public | DATABASE_PARAMS               | table | postgres
 public | DBS                           | table | postgres
 public | DB_PRIVS                      | table | postgres
 public | DELEGATION_TOKENS             | table | postgres
 public | FUNCS                         | table | postgres
 public | FUNC_RU                       | table | postgres
 public | GLOBAL_PRIVS                  | table | postgres
 public | IDXS                          | table | postgres
 public | INDEX_PARAMS                  | table | postgres
 public | I_SCHEMA                      | table | postgres
 public | KEY_CONSTRAINTS               | table | postgres
 public | MASTER_KEYS                   | table | postgres
 public | METASTORE_DB_PROPERTIES       | table | postgres
 
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

**NOTE** Giving the service in Kind cluster give read timeouts from Hive when it is trying to write to Minio. So for Mino the endpoint IP is mentiond in `metastore-cfg.yaml`. This means that every time the Kind cluster restarts the Endpoints have to reset and hive redeployed for now.

```
$ kubectl get ep | grep mini
mino-test-minio                10.244.1.14:9000,10.244.1.15:9000,10.244.1.2:9000 + 1 more...   13d

<property>
      <name>fs.s3a.endpoint</name>
      <value>http://10.244.1.14:9000</value>
</property>
```

## Step 2.3

First build the HiveMetastore Standalone

```
docker build -t hivemetastore:3.1.3.5 -f hive/Dockerfile ./hive
docker tag hivemetastore:3.1.3.5 alexcpn/hivemetastore:3.1.3.5
docker push alexcpn/hivemetastore:3.1.3.5
 ```

## Step 2.4

Install/Re-insall the hive Metadata server

```
kubectl delete -f hive/hive-meta-store-standalone.yaml
kubectl create -f hive/hive-meta-store-standalone.yaml
kubectl apply -f hive/metastore-cfg.yaml
```

# Step 4. Install Trino (PrestoSQL)

Configure the Postgres,S3, and Metastrore Service first in `trino\trino_cfg.yaml`

```
kubectl apply -f trino/trino_cfg.yaml
kubectl apply -f trino/trino.yaml
```

Port forward to see the UI

```
kubectl   port-forward svc/trino 8080  &
```

# Part 2

Create a table in S3 via Trino


Use the Minio UI to upload the parguet files to s3

![s3upload](https://i.imgur.com/wvPbQXZ.png)


## Create the schema for the Parquet files

## Access Trino CLI

Give the Service of trino in the server argument below

```
kubectl exec -it trino-cli -- /bin/bash 
/bin/trino --server trino:8080 --catalog hive --schema default

CREATE TABLE hive.mydatabase.mytable (
    title VARCHAR,
    description VARCHAR,
    author_id BIGINT,
    assignee_id BIGINT,
    iid BIGINT,
    labels VARCHAR,
    confidential BOOLEAN,
    created_at TIMESTAMP,
    references VARCHAR,
    severity VARCHAR,
    state VARCHAR,
    project_id BIGINT,
    issue_type VARCHAR,
    rtype VARCHAR,
    updated_at TIMESTAMP,
    web_url VARCHAR,
    closed_by VARCHAR,
    closed_at TIMESTAMP
)
WITH (
    format = 'PARQUET',
    external_location = 's3a://test/warehouse/mydatabase/'
);
```
If the path is right, it would have got all the rows in your Parquet files

```
select count(*) from mydatabase.mytable;
 _col0 
-------
 27748 
(1 row)

```

Here is a screen shot

![trino](https://i.imgur.com/cK22KH8.png)





