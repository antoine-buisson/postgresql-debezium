up:
	docker compose up --build --force-recreate -d

down:
	docker compose down -v --remove-orphans

consume-references:
	docker compose exec -T kafka-broker /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic dbserver1.public.book_references --from-beginning

consume-inventories:
	docker compose exec -T kafka-broker /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic dbserver1.public.book_inventories --from-beginning

consume-rentals:
	docker compose exec -T kafka-broker /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic dbserver1.public.book_rentals --from-beginning