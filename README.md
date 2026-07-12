# postgresql-debezium

This repository shows a minimal PostgreSQL -> Kafka -> Flink pipeline using Debezium.

## Quick start

1. Start the Docker stack:
   ```sh
   make up
   ```
2. Register the Debezium connector and initialize the database:
   ```sh
   make register
   ```
3. Run the Flink SQL example:
   ```sh
   make flink-sql
   ```

## What to configure

- `setup/setup.sh`
  - `table.include.list`: list the Postgres tables you want Debezium to capture.
  - `database.server.name`: keep this stable so Kafka topic names do not change.
  - `plugin.name`: `pgoutput` is the modern PostgreSQL connector plugin.

- `docker-compose.yaml`
  - `kafka-broker`: bootstraps Kafka at `localhost:9092`.
  - `kafka-connect`: exposes the Debezium REST API on `localhost:8083`.
  - `flink-sql-client`: now mounts `./setup` so Flink can run the example SQL.

- `flink.Dockerfile`
  - includes the Kafka connector jar needed by Flink to read from Kafka.
  - includes the Iceberg runtime jar if you later want to write to Iceberg.

- `setup/flink.kafka2iceberg.sql`
  - contains a sample source table reading the Debezium topic.
  - writes to a `print` sink so you can confirm the pipeline works.

## Useful commands

- `make status` — check the Debezium connector status
- `make consume` — view raw Kafka topic events
- `make psql` — open a Postgres shell
- `make logs` — tail the key container logs
- `make flink-sql` — execute the example Flink SQL script

## Notes for Flink beginners

- First verify Debezium is producing data with `make consume`.
- Then run `make flink-sql` to execute the Flink SQL script and watch the output.
- If you want a persistent sink later, replace `print` with Kafka, JDBC, or Iceberg.
