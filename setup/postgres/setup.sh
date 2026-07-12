#!/bin/bash

if [ -z "$POSTGRES_HOST" ]; then
  echo "POSTGRES_HOST is not set"
  exit 1
fi

if [ -z "$POSTGRES_PORT" ]; then
  echo "POSTGRES_PORT is not set. Using default port 5432"
  POSTGRES_PORT=5432
fi

until pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

psql postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB -f init.sql