FROM apache/spark:4.1.2-python3

RUN set -eux; \
    wget -P /opt/spark/jars \
      https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.13/4.1.2/spark-sql-kafka-0-10_2.13-4.1.2.jar \
      https://repo1.maven.org/maven2/org/apache/spark/spark-streaming-kafka-0-10_2.13/4.1.2/spark-streaming-kafka-0-10_2.13-4.1.2.jar \
      https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.13/4.1.2/spark-token-provider-kafka-0-10_2.13-4.1.2.jar \
      https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.7.1/kafka-clients-3.7.1.jar \
      https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar \
      https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-4.1_2.13/1.11.0/iceberg-spark-runtime-4.1_2.13-1.11.0.jar \
      https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.11.0/iceberg-aws-bundle-1.11.0.jar