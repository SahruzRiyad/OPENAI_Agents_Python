from flask import Flask, request, jsonify
import asyncio
from ai_agent_searching_storing import generate_response

app = Flask(__name__)

@app.route('/search',methods=['GET'])

def search():
    query = request.args.get('query')

    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400
    else:    
        result = asyncio.run(generate_response(query))
        response = {
            'success': True,
            'query': f'Search for: {query}',
            "result": result
        }
        return jsonify(response), 200


if __name__ == '__main__':
    app.run(debug=True)