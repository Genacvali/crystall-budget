"""API test configuration and fixtures."""
import pytest
import requests
import os
import json
from datetime import datetime, date
import tempfile
import sqlite3


@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API tests."""
    return os.getenv('API_BASE_URL', 'http://localhost:5000')


@pytest.fixture(scope="session")
def test_db():
    """Create test database for API tests."""
    # Create temporary database file
    db_file = tempfile.mktemp(suffix='.db')
    
    # Initialize database schema
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Basic table creation (simplified for testing)
    cursor.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100),
            telegram_id INTEGER UNIQUE,
            auth_type VARCHAR(20) DEFAULT 'email',
            currency VARCHAR(3) DEFAULT 'RUB',
            theme VARCHAR(10) DEFAULT 'light',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            limit_type VARCHAR(10) NOT NULL,
            limit_value DECIMAL(15,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (category_id) REFERENCES categories (id)
        );
        
        CREATE TABLE income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source VARCHAR(100) NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        
        -- Insert test user
        INSERT INTO users (id, name, telegram_id, auth_type) 
        VALUES (1, 'Test User', 12345, 'telegram');
        
        -- Insert test category
        INSERT INTO categories (user_id, name, limit_type, limit_value)
        VALUES (1, 'Тестовая категория', 'fixed', 10000.00);
    """)
    
    conn.commit()
    conn.close()
    
    yield db_file
    
    # Cleanup
    os.unlink(db_file)


@pytest.fixture(scope="function")
def api_client(api_base_url):
    """HTTP client with session for API tests."""
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    # Mock authentication for testing
    session.cookies.set('session', 'test_session_token')
    
    class APIClient:
        def __init__(self, base_url, session):
            self.base_url = base_url
            self.session = session
        
        def get(self, endpoint, **kwargs):
            return self.session.get(f"{self.base_url}{endpoint}", **kwargs)
        
        def post(self, endpoint, **kwargs):
            return self.session.post(f"{self.base_url}{endpoint}", **kwargs)
        
        def put(self, endpoint, **kwargs):
            return self.session.put(f"{self.base_url}{endpoint}", **kwargs)
        
        def delete(self, endpoint, **kwargs):
            return self.session.delete(f"{self.base_url}{endpoint}", **kwargs)
        
        def patch(self, endpoint, **kwargs):
            return self.session.patch(f"{self.base_url}{endpoint}", **kwargs)
    
    return APIClient(api_base_url, session)


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        'id': 1,
        'name': 'Test User',
        'telegram_id': 12345,
        'auth_type': 'telegram',
        'currency': 'RUB',
        'theme': 'light'
    }


@pytest.fixture  
def test_category_data():
    """Test category data."""
    return {
        'name': 'API Test Category',
        'limit_type': 'fixed',
        'limit_value': 5000.00
    }


@pytest.fixture
def test_expense_data():
    """Test expense data."""
    return {
        'category_id': 1,
        'amount': 1500.50,
        'description': 'API Test Expense',
        'date': date.today().isoformat()
    }


@pytest.fixture
def test_income_data():
    """Test income data.""" 
    return {
        'source': 'API Test Income',
        'amount': 50000.00,
        'date': date.today().isoformat()
    }


class APITestHelpers:
    """Helper methods for API testing."""
    
    @staticmethod
    def assert_response_success(response, expected_status=200):
        """Assert response is successful."""
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text}"
        )
    
    @staticmethod
    def assert_response_error(response, expected_status=400):
        """Assert response is error."""
        assert response.status_code >= expected_status
    
    @staticmethod
    def assert_json_structure(data, required_fields):
        """Assert JSON has required fields."""
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    @staticmethod
    def assert_pagination(data, expected_fields=['items', 'total', 'page', 'per_page']):
        """Assert pagination structure."""
        for field in expected_fields:
            assert field in data, f"Missing pagination field: {field}"


@pytest.fixture
def helpers():
    """Provide API test helpers."""
    return APITestHelpers