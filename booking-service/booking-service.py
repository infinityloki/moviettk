# booking-service/app.py
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import mysql.connector
import json
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

app = Flask(__name__)

# JWT Configuration (same secret as auth service)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET', 'super-secret-key')
jwt = JWTManager(app)

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'mysql-db'),
        user=os.environ.get('DB_USER', 'movieuser'),
        password=os.environ.get('DB_PASSWORD', 'moviepass'),
        database=os.environ.get('DB_NAME', 'moviebooking')
    )

# Get available seats for a show
@app.route('/shows/<int:show_id>/seats', methods=['GET'])
def get_available_seats(show_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get screen capacity
        cursor.execute('''
            SELECT sc.total_seats 
            FROM shows s 
            JOIN screens sc ON s.screen_id = sc.id 
            WHERE s.id = %s
        ''', (show_id,))
        screen = cursor.fetchone()
        
        if not screen:
            return jsonify({'message': 'Show not found'}), 404
        
        # Get booked seats
        cursor.execute('''
            SELECT seats 
            FROM bookings 
            WHERE show_id = %s AND status = 'confirmed'
        ''', (show_id,))
        booked_seats_records = cursor.fetchall()
        
        # Flatten all booked seats
        booked_seats = []
        for record in booked_seats_records:
            booked_seats.extend(json.loads(record['seats']))
        
        # Generate all seats
        total_seats = screen['total_seats']
        all_seats = [f"{row}{seat}" for row in "ABCDEFGHIJ" for seat in range(1, 11) if (ord(row) - 65) * 10 + seat <= total_seats]
        
        # Available seats are all seats minus booked seats
        available_seats = [seat for seat in all_seats if seat not in booked_seats]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'available_seats': available_seats,
            'booked_seats': booked_seats,
            'total_seats': total_seats
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Book seats for a show
@app.route('/bookings', methods=['POST'])
@jwt_required()
def create_booking():
    user_id = get_jwt_identity()
    data = request.get_json()
    show_id = data.get('show_id')
    seats = data.get('seats')  # List of seat numbers
    
    if not show_id or not seats:
        return jsonify({'message': 'Missing show_id or seats'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get show details and price
        cursor.execute('''
            SELECT s.price, m.title, s.show_time, th.name as theater_name, sc.name as screen_name
            FROM shows s
            JOIN movies m ON s.movie_id = m.id
            JOIN screens sc ON s.screen_id = sc.id
            JOIN theaters th ON sc.theater_id = th.id
            WHERE s.id = %s
        ''', (show_id,))
        show = cursor.fetchone()
        
        if not show:
            return jsonify({'message': 'Show not found'}), 404
        
        # Check if seats are available
        cursor.execute('''
            SELECT seats 
            FROM bookings 
            WHERE show_id = %s AND status = 'confirmed'
        ''', (show_id,))
        booked_seats_records = cursor.fetchall()
        
        booked_seats = []
        for record in booked_seats_records:
            booked_seats.extend(json.loads(record['seats']))
        
        for seat in seats:
            if seat in booked_seats:
                return jsonify({'message': f'Seat {seat} is already booked'}), 400
        
        # Calculate total amount
        total_amount = show['price'] * len(seats)
        
        # Create booking
        cursor.execute('''
            INSERT INTO bookings (user_id, show_id, seats, total_amount)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, show_id, json.dumps(seats), total_amount))
        
        booking_id = cursor.lastrowid
        conn.commit()
        
        # Get booking details for response
        cursor.execute('''
            SELECT b.*, m.title as movie_title, s.show_time, th.name as theater_name, sc.name as screen_name
            FROM bookings b
            JOIN shows s ON b.show_id = s.id
            JOIN movies m ON s.movie_id = m.id
            JOIN screens sc ON s.screen_id = sc.id
            JOIN theaters th ON sc.theater_id = th.id
            WHERE b.id = %s
        ''', (booking_id,))
        booking = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Booking successful',
            'booking_id': booking_id,
            'booking_details': booking
        }), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Get user bookings
@app.route('/bookings', methods=['GET'])
@jwt_required()
def get_user_bookings():
    user_id = get_jwt_identity()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT b.*, m.title as movie_title, m.poster_url, s.show_time, th.name as theater_name, sc.name as screen_name
            FROM bookings b
            JOIN shows s ON b.show_id = s.id
            JOIN movies m ON s.movie_id = m.id
            JOIN screens sc ON s.screen_id = sc.id
            JOIN theaters th ON sc.theater_id = th.id
            WHERE b.user_id = %s
            ORDER BY b.booking_time DESC
        ''', (user_id,))
        
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(bookings), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Generate ticket PDF
@app.route('/bookings/<int:booking_id>/ticket', methods=['GET'])
@jwt_required()
def generate_ticket(booking_id):
    user_id = get_jwt_identity()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT b.*, m.title as movie_title, s.show_time, th.name as theater_name, 
                   th.location, sc.name as screen_name, u.username, u.email
            FROM bookings b
            JOIN shows s ON b.show_id = s.id
            JOIN movies m ON s.movie_id = m.id
            JOIN screens sc ON s.screen_id = sc.id
            JOIN theaters th ON sc.theater_id = th.id
            JOIN users u ON b.user_id = u.id
            WHERE b.id = %s AND b.user_id = %s
        ''', (booking_id, user_id))
        
        booking = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        # Create PDF ticket
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Add content to PDF
        c.setFont("Helvetica-Bold", 20)
        c.drawString(100, height - 100, "Movie Ticket")
        c.line(100, height - 110, width - 100, height - 110)
        
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 140, f"Movie: {booking['movie_title']}")
        c.drawString(100, height - 160, f"Theater: {booking['theater_name']}")
        c.drawString(100, height - 180, f"Screen: {booking['screen_name']}")
        c.drawString(100, height - 200, f"Show Time: {booking['show_time'].strftime('%Y-%m-%d %H:%M')}")
        c.drawString(100, height - 220, f"Seats: {', '.join(json.loads(booking['seats']))}")
        c.drawString(100, height - 240, f"Total Amount: ${booking['total_amount']}")
        c.drawString(100, height - 260, f"Customer: {booking['username']}")
        
        c.drawString(100, height - 300, "Thank you for your booking!")
        
        c.showPage()
        c.save()
        
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Return PDF as base64 encoded string
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        return jsonify({
            'ticket_pdf': pdf_base64,
            'filename': f'ticket_{booking_id}.pdf'
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
