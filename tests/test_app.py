import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_chat_endpoint(client):
    """Test the /chat endpoint."""
    response = client.post('/chat', json={'query': 'hello'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'response' in data
    assert 'sources' in data
    assert isinstance(data['sources'], list)
    assert "hello" in data['response']
