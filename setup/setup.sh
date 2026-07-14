#!/bin/sh

# ============================
#       Bins and helpers
# ============================

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

run_postgres_query_on_db () {
  psql postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$1 -c "$2";
}

# ============================
#       Configuration
# ============================

add_configuration "$POSTGRES_HOST" "POSTGRES_HOST"
add_configuration "$POSTGRES_PORT" "POSTGRES_PORT" 5432

add_configuration "$POSTGRES_DB" "POSTGRES_DB"
add_configuration "$MAIN_DB" "MAIN_DB"
add_configuration "$MONITORING_DB" "MONITORING_DB"

add_configuration "$POSTGRES_USER" "POSTGRES_USER"
add_configuration "$POSTGRES_PASSWORD" "POSTGRES_PASSWORD"
add_configuration "$EVENT_GENERATOR_USER" "EVENT_GENERATOR_USER"
add_configuration "$EVENT_GENERATOR_PASSWORD" "EVENT_GENERATOR_PASSWORD"
add_configuration "$DEBEZIUM_USER" "DEBEZIUM_USER"
add_configuration "$DEBEZIUM_PASSWORD" "DEBEZIUM_PASSWORD"
add_configuration "$MONITORING_USER" "MONITORING_USER"
add_configuration "$MONITORING_PASSWORD" "MONITORING_PASSWORD"

add_configuration "$KAFKA_HOST" "KAFKA_HOST"
add_configuration "$KAFKA_PORT" "KAFKA_PORT" 29092
add_configuration "$KAFKA_CONNECT_HOST" "KAFKA_CONNECT_HOST"
add_configuration "$KAFKA_CONNECT_PORT" "KAFKA_CONNECT_PORT" 8083

# ============================
#       Health Checks
# ============================

until pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

until nc -z "$KAFKA_HOST" "$KAFKA_PORT"; do
    echo "Waiting for Kafka to be ready..."
    sleep 2
done

until nc -z "$KAFKA_CONNECT_HOST" "$KAFKA_CONNECT_PORT"; do
    echo "Waiting for Kafka Connect to be ready..."
    sleep 2
done

# ============================
#       Postgres Setup
# ============================

run_postgres_query_on_db "$POSTGRES_DB" "CREATE DATABASE $MAIN_DB;"

run_postgres_query_on_db "$POSTGRES_DB" "CREATE DATABASE $MONITORING_DB;"

run_postgres_query_on_db "$POSTGRES_DB" "CREATE ROLE $EVENT_GENERATOR_USER WITH LOGIN PASSWORD '$EVENT_GENERATOR_PASSWORD';"
run_postgres_query_on_db "$MAIN_DB" "GRANT ALL PRIVILEGES ON SCHEMA public TO $EVENT_GENERATOR_USER;"

run_postgres_query_on_db "$POSTGRES_DB" "CREATE ROLE $DEBEZIUM_USER WITH SUPERUSER LOGIN REPLICATION PASSWORD '$DEBEZIUM_PASSWORD';"
run_postgres_query_on_db "$MAIN_DB" "GRANT ALL PRIVILEGES ON DATABASE $MAIN_DB TO $DEBEZIUM_USER;"

run_postgres_query_on_db "$POSTGRES_DB" "CREATE ROLE $MONITORING_USER WITH SUPERUSER LOGIN REPLICATION PASSWORD '$MONITORING_PASSWORD';"
run_postgres_query_on_db "$MONITORING_DB" "GRANT ALL PRIVILEGES ON DATABASE $MONITORING_DB TO $MONITORING_USER;"

# ============================
#       Debezium Setup
# ============================

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
    "database.dbname": "$MAIN_DB",
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