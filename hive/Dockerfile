FROM adoptopenjdk/openjdk11:alpine-jre
WORKDIR /opt

ENV HADOOP_VERSION=3.3.0
ENV METASTORE_VERSION=3.1.3

ENV HADOOP_HOME=/opt/hadoop-${HADOOP_VERSION}
ENV HIVE_HOME=/opt/apache-hive-metastore-${METASTORE_VERSION}-bin

COPY metastore-log4j2.properties .

RUN apk add --no-cache bash curl && \
curl -L https://repo1.maven.org/maven2/org/apache/hive/hive-standalone-metastore/${METASTORE_VERSION}/hive-standalone-metastore-${METASTORE_VERSION}-bin.tar.gz | tar zxf - && \
    curl -L https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz | tar zxf - 

#needed to fix nosuchmethoderror
#see https://issues.apache.org/jira/browse/HIVE-22915
RUN rm /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/guava-19.0.jar && \
    cp /opt/hadoop-${HADOOP_VERSION}/share/hadoop/hdfs/lib/guava-27.0-jre.jar /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib


# Download and install the Postgres connector.
RUN curl -L https://jdbc.postgresql.org/download/postgresql-42.4.0.jar -o \
	 /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/postgresql-42.4.0.jar 

# Download and install the S3 related Jars
RUN curl -L https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_VERSION}/hadoop-aws-${HADOOP_VERSION}.jar -o \
  /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/hadoop-aws-${HADOOP_VERSION}.jar \
&& curl -L https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk/1.12.238/aws-java-sdk-1.12.238.jar -o \
/opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/aws-java-sdk-1.12.238.jar \
&& curl -L https://repo1.maven.org/maven2/net/java/dev/jets3t/jets3t/0.9.4/jets3t-0.9.4.jar -o \
 /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/jets3t-0.9.4.jar \
&& curl -L https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-core/1.12.238/aws-java-sdk-core-1.12.238.jar -o \
/opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/aws-java-sdk-core-1.12.238.jar \
&& curl -L https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.238/aws-java-sdk-bundle-1.12.238.jar -o \
/opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/aws-java-sdk-bundle-1.12.238.jar \
# Below for transcaction bug https://github.com/trinodb/trino/issues/6980
&& curl -L  https://repo1.maven.org/maven2/org/apache/hive/hive-exec/3.1.3/hive-exec-3.1.3.jar -o \
/opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/hive-exec-3.1.3.jar \
&& curl -L https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-web/2.17.2/log4j-web-2.17.2.jar -o \
/opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/log4j-web-2.17.2.jar


# Below Only if you are using built in DB

#RUN /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/bin/schematool -initSchema -dbType derby
#persist the database changes
#VOLUME /opt/metastore_db

#metastore runs on this port
EXPOSE 9083

CMD /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/bin/start-metastore