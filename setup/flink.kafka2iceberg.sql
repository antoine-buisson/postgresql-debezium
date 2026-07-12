CREATE TABLE country (
  id INT,
  name STRING,
  code STRING,
  PRIMARY KEY (id) NOT ENFORCED
) WITH (
  'connector' = 'kafka',
  'topic' = 'dbserver1.public.country',
  'properties.bootstrap.servers' = 'kafka-broker:29092',
  'properties.group.id' = 'flink-country-group',
  'scan.startup.mode' = 'earliest-offset',
  'format' = 'debezium-json'
);

CREATE TABLE city (
  id INT,
  name STRING,
  country_id INT,
  population INT,
  PRIMARY KEY (id) NOT ENFORCED
) WITH (
  'connector' = 'kafka',
  'topic' = 'dbserver1.public.city',
  'properties.bootstrap.servers' = 'kafka-broker:29092',
  'properties.group.id' = 'flink-city-group',
  'scan.startup.mode' = 'earliest-offset',
  'format' = 'debezium-json'
);

CREATE TABLE print_country (
  id INT,
  name STRING,
  code STRING
) WITH (
  'connector' = 'print'
);

CREATE TABLE print_city (
  id INT,
  name STRING,
  country_id INT,
  population INT
) WITH (
  'connector' = 'print'
);

INSERT INTO print_country
SELECT id, name, code FROM country;

INSERT INTO print_city
SELECT id, name, country_id, population FROM city;
