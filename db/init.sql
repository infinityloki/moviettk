-- db/init.sql
CREATE DATABASE IF NOT EXISTS moviebooking;
USE moviebooking;

-- Users table for authentication
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Movies table
CREATE TABLE movies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    duration INT, -- in minutes
    genre VARCHAR(100),
    release_date DATE,
    poster_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Theaters table
CREATE TABLE theaters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Screens table
CREATE TABLE screens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    theater_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    total_seats INT NOT NULL,
    FOREIGN KEY (theater_id) REFERENCES theaters(id) ON DELETE CASCADE
);

-- Shows table
CREATE TABLE shows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    screen_id INT NOT NULL,
    show_time DATETIME NOT NULL,
    price DECIMAL(8, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

-- Bookings table
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    show_id INT NOT NULL,
    seats TEXT NOT NULL, -- JSON array of seat numbers
    total_amount DECIMAL(10, 2) NOT NULL,
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('confirmed', 'cancelled') DEFAULT 'confirmed',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (show_id) REFERENCES shows(id) ON DELETE CASCADE
);

-- Insert sample data
INSERT INTO users (username, password_hash, email) VALUES 
('john_doe', '$2b$12$r8VKX6W3L7d2s1qA0pG8EeB6vC5dF3gH4jK2lM1nV7bR8tY9zX0u', 'john@example.com'),
('jane_smith', '$2b$12$r8VKX6W3L7d2s1qA0pG8EeB6vC5dF3gH4jK2lM1nV7bR8tY9zX0u', 'jane@example.com');

INSERT INTO movies (title, description, duration, genre, release_date, poster_url) VALUES 
('Inception', 'A thief who steals corporate secrets through dream-sharing technology.', 148, 'Sci-Fi', '2010-07-16', '/uploads/inception.jpg'),
('The Dark Knight', 'Batman sets out to dismantle the remaining criminal organizations in Gotham.', 152, 'Action', '2008-07-18', '/uploads/dark_knight.jpg');

INSERT INTO theaters (name, location, latitude, longitude) VALUES 
('City Cinemas', '123 Main St, New York', 40.7128, -74.0060),
('Downtown Theater', '456 Broadway, New York', 40.7195, -74.0082);

INSERT INTO screens (theater_id, name, total_seats) VALUES 
(1, 'Screen 1', 100),
(1, 'Screen 2', 80),
(2, 'Main Hall', 120);

INSERT INTO shows (movie_id, screen_id, show_time, price) VALUES 
(1, 1, '2023-12-15 18:00:00', 12.50),
(1, 2, '2023-12-15 21:00:00', 12.50),
(2, 3, '2023-12-15 19:30:00', 14.00);
