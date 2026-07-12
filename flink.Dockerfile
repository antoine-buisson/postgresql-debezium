FROM flink:2.3.0-scala_2.12
RUN wget -P /opt/flink/lib https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/4.0.0-2.0/flink-sql-connector-kafka-4.0.0-2.0.jar
RUN wget -P /opt/flink/lib https://repo.maven.apache.org/maven2/org/apache/iceberg/iceberg-flink-runtime-1.19/1.10.2/iceberg-flink-runtime-1.19-1.10.2.jar