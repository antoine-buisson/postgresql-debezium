#!/bin/bash

if [ -z "$KAFKA_HOST" ]; then
  echo "KAFKA_HOST is not set"
  exit 1
fi

if [ -z "$KAFKA_PORT" ]; then
  echo "KAFKA_PORT is not set. Using default port 29092"
  KAFKA_PORT=29092
fi

until nc -z "$KAFKA_HOST" "$KAFKA_PORT"; do
    echo "Waiting for Kafka to be ready..."
    sleep 2
done

/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$KAFKA_HOST:$KAFKA_PORT" --create --if-not-exists --topic test-topic
