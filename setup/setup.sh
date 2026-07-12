#!/bin/sh

apk add --no-cache postgresql-client curl netcat-openbsd

add_configuration () {
  if [ -z "$1" ]; then
    if [ -z "$3" ]; then
      echo "$2 is not set"
      exit 1
    fi
    echo "$2 is not set. Using default value $3"
    eval "$2=$3"
  fi
}

add_configuration "$POSTGRES_HOST" "POSTGRES_HOST"
add_configuration "$POSTGRES_PORT" "POSTGRES_PORT" 5432
add_configuration "$POSTGRES_USER" "POSTGRES_USER"
add_configuration "$POSTGRES_PASSWORD" "POSTGRES_PASSWORD"
add_configuration "$POSTGRES_DB" "POSTGRES_DB"
add_configuration "$KAFKA_HOST" "KAFKA_HOST"
add_configuration "$KAFKA_PORT" "KAFKA_PORT" 29092
add_configuration "$KAFKA_CONNECT_HOST" "KAFKA_CONNECT_HOST"
add_configuration "$KAFKA_CONNECT_PORT" "KAFKA_CONNECT_PORT" 8083
add_configuration "$DEBEZIUM_USER" "DEBEZIUM_USER"
add_configuration "$DEBEZIUM_PASSWORD" "DEBEZIUM_PASSWORD"

until pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

psql postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/postgres \
    -c "CREATE DATABASE $POSTGRES_DB;"

psql postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB \
    -c "CREATE ROLE $DEBEZIUM_USER WITH SUPERUSER LOGIN REPLICATION PASSWORD '$DEBEZIUM_PASSWORD';"

psql postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB \
    -c "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $DEBEZIUM_USER;"

until nc -z "$KAFKA_HOST" "$KAFKA_PORT"; do
    echo "Waiting for Kafka to be ready..."
    sleep 2
done

until nc -z "$KAFKA_CONNECT_HOST" "$KAFKA_CONNECT_PORT"; do
    echo "Waiting for Kafka Connect to be ready..."
    sleep 2
done

connector_payload=$(cat <<EOF
{
  "name": "postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "plugin.name": "pgoutput",
    "database.hostname": "$POSTGRES_HOST",
    "database.port": "$POSTGRES_PORT",
    "database.user": "$DEBEZIUM_USER",
    "database.password": "$DEBEZIUM_PASSWORD",
    "database.dbname": "$POSTGRES_DB",
    "database.server.name": "postgresql",
    "topic.prefix": "dbserver1"
  }
}
EOF
)

if curl -fsS "http://$KAFKA_CONNECT_HOST:$KAFKA_CONNECT_PORT/connectors/postgres-connector/status" >/dev/null 2>&1; then
    connector_status=$(curl -fsS "http://$KAFKA_CONNECT_HOST:$KAFKA_CONNECT_PORT/connectors/postgres-connector/status")
    if echo "$connector_status" | grep -q '"state":"FAILED"'; then
        echo "Recreating connector after role or config change"
        curl -fsS -X DELETE "http://$KAFKA_CONNECT_HOST:$KAFKA_CONNECT_PORT/connectors/postgres-connector" >/dev/null 2>&1 || true
        echo "$connector_payload" | curl -fsS -X POST http://$KAFKA_CONNECT_HOST:$KAFKA_CONNECT_PORT/connectors \
          -H "Content-Type: application/json" \
          --data-binary @-
    else
        echo "Connector is already running"
    fi
else
    echo "$connector_payload" | curl -fsS -X POST http://$KAFKA_CONNECT_HOST:$KAFKA_CONNECT_PORT/connectors \
      -H "Content-Type: application/json" \
      --data-binary @-
fi