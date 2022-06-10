FROM adoptopenjdk/openjdk11:alpine-jre
WORKDIR /opt

ENV HADOOP_VERSION=3.3.0
ENV METASTORE_VERSION=3.1.3

ENV HADOOP_HOME=/opt/hadoop-${HADOOP_VERSION}
ENV HIVE_HOME=/opt/apache-hive-metastore-${METASTORE_VERSION}-bin

RUN apk add --no-cache bash curl && curl -L https://repo1.maven.org/maven2/org/apache/hive/hive-standalone-metastore/${METASTORE_VERSION}/hive-standalone-metastore-${METASTORE_VERSION}-bin.tar.gz | tar zxf - && \
    curl -L https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz | tar zxf - 

#needed to fix nosuchmethoderror
#see https://issues.apache.org/jira/browse/HIVE-22915
RUN rm /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/guava-19.0.jar && \
    cp /opt/hadoop-${HADOOP_VERSION}/share/hadoop/hdfs/lib/guava-27.0-jre.jar /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib


# Download and install the mysql connector.
RUN curl -L https://jdbc.postgresql.org/download/postgresql-42.4.0.jar -o /opt/postgresql-42.4.0.jar \
	&& ln -s /opt/postgresql-42.4.0.jar  /opt/hadoop-${HADOOP_VERSION}/share/hadoop/common/lib/ \
	&& ln -s /opt/postgresql-42.4.0.jar  /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/lib/     

RUN /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/bin/schematool -initSchema -dbType derby

#persist the database changes
VOLUME /opt/metastore_db

#metastore runs on this port
EXPOSE 9083

CMD /opt/apache-hive-metastore-${METASTORE_VERSION}-bin/bin/start-metastore