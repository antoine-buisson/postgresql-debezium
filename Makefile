start:
	docker compose down -v --remove-orphans && docker compose up -d

up:
	docker compose up --build --force-recreate -d

down:
	docker compose down -v --remove-orphans

status:
	curl -s http://localhost:8083/connectors/postgres-connector/status

register:
	docker compose run --rm setup

consume:
	docker compose exec -T kafka-broker /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic dbserver1.public.book_references --from-beginning

insert-random:
	docker compose exec -T postgres psql -U postgres -d world_data -c "INSERT INTO country (id, name, code) VALUES ($$(date +%s), 'Random-$$(date +%H%M%S)', 'R$$(date +%H%M%S)');"

psql:
	docker compose exec -T postgres psql -U postgres -d world_data

logs:
	docker compose logs -f postgres kafka-broker kafka-connect setup

flink-sql:
	docker compose run flink-sql-client
