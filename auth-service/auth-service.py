# auth-service/app.py
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
from datetime import timedelta
import os

app = Flask(__name__)
bcrypt = Bcrypt(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET', 'super-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'mysql-db'),
        user=os.environ.get('DB_USER', 'movieuser'),
        password=os.environ.get('DB_PASSWORD', 'moviepass'),
        database=os.environ.get('DB_NAME', 'moviebooking')
    )

# User registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if not username or not password or not email:
        return jsonify({'message': 'Missing required fields'}), 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)',
            (username, hashed_password, email)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'User created successfully'}), 201
    except mysql.connector.IntegrityError:
        return jsonify({'message': 'Username or email already exists'}), 400
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# User login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Missing username or password'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and bcrypt.check_password_hash(user['password_hash'], password):
            access_token = create_access_token(identity=user['id'])
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user_id': user['id'],
                'username': user['username']
            }), 200
        else:
            return jsonify({'message': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# User logout (client-side token removal)
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # JWT is stateless, so logout is handled client-side by removing the token
    return jsonify({'message': 'Logout successful'}), 200

# Protected route example
@app.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, username, email, created_at FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return jsonify(user), 200
        else:
            return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
