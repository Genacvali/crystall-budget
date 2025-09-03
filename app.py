from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import jwt
import argon2
import uuid
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
DB_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/crystall_budget')

ph = argon2.PasswordHasher()

def get_db():
    return psycopg2.connect(DB_URL)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user_id = data['userId']
        except:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user_id, *args, **kwargs)
    return decorated

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    try:
        password_hash = ph.hash(password)
        user_id = str(uuid.uuid4())
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute(
            'INSERT INTO "User" (id, email, "passwordHash") VALUES (%s, %s, %s)',
            (user_id, email, password_hash)
        )
        conn.commit()
        
        token = jwt.encode({
            'userId': user_id,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, JWT_SECRET)
        
        cur.close()
        conn.close()
        
        return jsonify({'token': token})
        
    except psycopg2.IntegrityError:
        return jsonify({'error': 'User already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('SELECT id, "passwordHash" FROM "User" WHERE email = %s', (email,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user_id, password_hash = user
        ph.verify(password_hash, password)
        
        token = jwt.encode({
            'userId': user_id,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, JWT_SECRET)
        
        cur.close()
        conn.close()
        
        return jsonify({'token': token})
        
    except argon2.exceptions.VerifyMismatchError:
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/me', methods=['GET'])
@token_required
def get_me(current_user_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('SELECT id, email FROM "User" WHERE id = %s', (current_user_id,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_id, email = user
        
        cur.close()
        conn.close()
        
        return jsonify({'id': user_id, 'email': email})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=False)