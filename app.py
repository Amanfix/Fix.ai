from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    query = data.get('query')

    # In a real application, you would process the query,
    # search the web, and use an LLM to generate a response.
    # For this example, we'll return a dummy response.

    dummy_response = {
        "response": f"This is a dummy response to your query: '{query}'. In a real application, I would provide a comprehensive answer with sources.",
        "sources": [
            {"title": "Dummy Source 1", "url": "https://example.com/source1"},
            {"title": "Dummy Source 2", "url": "https://example.com/source2"}
        ]
    }
    return jsonify(dummy_response)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
