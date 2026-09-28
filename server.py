import os
import json
import sqlite3
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

DB_FILE = 'restaurant.db'
PORT = 8000

def init_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            request_type TEXT NOT NULL,
            guest_count TEXT,
            preferred_date TEXT,
            preferred_time TEXT,
            special_notes TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[DB] SQLite database initialized at '{DB_FILE}'")

class RestaurantRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # Route: API to get all reservations for Admin Dashboard
        if self.path == '/api/reservations':
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('SELECT id, name, phone, request_type, guest_count, preferred_date, preferred_time, special_notes, status, created_at FROM reservations ORDER BY id DESC')
                rows = cursor.fetchall()
                conn.close()

                reservations = [
                    {
                        "id": row[0],
                        "name": row[1],
                        "phone": row[2],
                        "request_type": row[3],
                        "guest_count": row[4],
                        "preferred_date": row[5],
                        "preferred_time": row[6],
                        "special_notes": row[7],
                        "status": row[8],
                        "created_at": row[9]
                    }
                    for row in rows
                ]

                response_bytes = json.dumps({"status": "success", "data": reservations}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)
            except Exception as e:
                self.send_error(500, f"Database error: {str(e)}")
            return

        # Default: Serve static files (index.html, admin.html, styles, scripts)
        return super().do_GET()

    def do_POST(self):
        # Route: API to create new reservation or takeaway request
        if self.path == '/api/reservations':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                name = data.get('name', '').strip()
                phone = data.get('phone', '').strip()
                request_type = data.get('request_type', 'Table Reservation')
                guest_count = data.get('guest_count', '3-5 People')
                preferred_date = data.get('preferred_date', '')
                preferred_time = data.get('preferred_time', '')
                special_notes = data.get('special_notes', '')

                if not name or not phone:
                    response_bytes = json.dumps({"status": "error", "message": "Name and phone number are required."}).encode('utf-8')
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(response_bytes)))
                    self.end_headers()
                    self.wfile.write(response_bytes)
                    return

                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO reservations (name, phone, request_type, guest_count, preferred_date, preferred_time, special_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, phone, request_type, guest_count, preferred_date, preferred_time, special_notes))
                conn.commit()
                new_id = cursor.lastrowid
                conn.close()

                print(f"[DB] New reservation saved: ID {new_id} - {name} ({phone})")

                response_bytes = json.dumps({
                    "status": "success",
                    "id": new_id,
                    "message": "Reservation saved successfully in database!"
                }).encode('utf-8')

                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)
            except Exception as e:
                self.send_error(500, f"Error processing reservation: {str(e)}")
            return

        # Route: API to update status of a reservation
        if self.path == '/api/reservations/update_status':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                res_id = data.get('id')
                new_status = data.get('status', 'Pending')

                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('UPDATE reservations SET status = ? WHERE id = ?', (new_status, res_id))
                conn.commit()
                conn.close()

                response_bytes = json.dumps({"status": "success", "message": "Status updated!"}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)
            except Exception as e:
                self.send_error(500, f"Error updating status: {str(e)}")
            return

        self.send_error(404, "Endpoint not found")

def run(server_class=HTTPServer, handler_class=RestaurantRequestHandler, port=PORT):
    init_db()
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"[SERVER] Restaurant API & Web Server running on http://localhost:{port}")
    print(f"[ADMIN] Admin Dashboard available at http://localhost:{port}/admin.html")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
