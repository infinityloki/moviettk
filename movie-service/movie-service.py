# movie-service/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import mysql.connector
from werkzeug.utils import secure_filename
import os
import uuid

app = Flask(__name__)

# JWT Configuration (same secret as auth service)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET', 'super-secret-key')
jwt = JWTManager(app)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'mysql-db'),
        user=os.environ.get('DB_USER', 'movieuser'),
        password=os.environ.get('DB_PASSWORD', 'moviepass'),
        database=os.environ.get('DB_NAME', 'moviebooking')
    )

# Get all movies
@app.route('/movies', methods=['GET'])
def get_movies():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM movies ORDER BY release_date DESC')
        movies = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(movies), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Get movie by ID
@app.route('/movies/<int:movie_id>', methods=['GET'])
def get_movie(movie_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM movies WHERE id = %s', (movie_id,))
        movie = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if movie:
            return jsonify(movie), 200
        else:
            return jsonify({'message': 'Movie not found'}), 404
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Add new movie (admin function)
@app.route('/movies', methods=['POST'])
@jwt_required()
def add_movie():
    # In a real application, you would check if the user is an admin
    data = request.form
    title = data.get('title')
    description = data.get('description')
    duration = data.get('duration')
    genre = data.get('genre')
    release_date = data.get('release_date')
    
    if not title or not description:
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Handle file upload
    poster_url = None
    if 'poster' in request.files:
        file = request.files['poster']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Generate unique filename
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            poster_url = f"/uploads/{unique_filename}"
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO movies (title, description, duration, genre, release_date, poster_url) VALUES (%s, %s, %s, %s, %s, %s)',
            (title, description, duration, genre, release_date, poster_url)
        )
        conn.commit()
        movie_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Movie added successfully', 'movie_id': movie_id}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Get theaters by location
@app.route('/theaters', methods=['GET'])
def get_theaters():
    try:
        lat = request.args.get('lat')
        lng = request.args.get('lng')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if lat and lng:
            # Simple distance calculation (for demonstration)
            query = """
                SELECT *, 
                (6371 * acos(cos(radians(%s)) * cos(radians(latitude)) * 
                cos(radians(longitude) - radians(%s)) + sin(radians(%s)) * 
                sin(radians(latitude)))) AS distance 
                FROM theaters 
                ORDER BY distance
            """
            cursor.execute(query, (lat, lng, lat))
        else:
            cursor.execute('SELECT * FROM theaters')
            
        theaters = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(theaters), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Get shows for a movie
@app.route('/movies/<int:movie_id>/shows', methods=['GET'])
def get_movie_shows(movie_id):
    try:
        date = request.args.get('date')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if date:
            query = """
                SELECT s.*, th.name as theater_name, th.location, sc.name as screen_name
                FROM shows s
                JOIN screens sc ON s.screen_id = sc.id
                JOIN theaters th ON sc.theater_id = th.id
                WHERE s.movie_id = %s AND DATE(s.show_time) = %s
                ORDER BY s.show_time
            """
            cursor.execute(query, (movie_id, date))
        else:
            query = """
                SELECT s.*, th.name as theater_name, th.location, sc.name as screen_name
                FROM shows s
                JOIN screens sc ON s.screen_id = sc.id
                JOIN theaters th ON sc.theater_id = th.id
                WHERE s.movie_id = %s AND s.show_time > NOW()
                ORDER BY s.show_time
            """
            cursor.execute(query, (movie_id,))
            
        shows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(shows), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
