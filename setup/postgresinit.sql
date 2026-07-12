CREATE TABLE IF NOT EXISTS country (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS city (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country_id INT,
    population INT,
    FOREIGN KEY (country_id) REFERENCES country(id)
);

-- Mock data

INSERT INTO country (id, name, code) VALUES
(1, 'France', 'FR'),
(2, 'Canada', 'CA'),
(3, 'China', 'CN');

INSERT INTO city (id, name, country_id, population) VALUES
(1, 'Paris', 1, 2148327),
(2, 'Lyon', 1, 515695),
(3, 'Toronto', 2, 2731571),
(4, 'Vancouver', 2, 631486),
(5, 'Beijing', 3, 21542000),
(6, 'Shanghai', 3, 24183300);