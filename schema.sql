CREATE DATABASE IF NOT EXISTS lost_items_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE lost_items_db;

CREATE TABLE IF NOT EXISTS items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    contact VARCHAR(255),
    photo TEXT
);
