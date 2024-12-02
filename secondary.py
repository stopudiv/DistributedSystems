from flask import Flask, request, jsonify
import time

app = Flask(__name__)
replicated_messages = []

@app.route('/replicate', methods=['POST'])
def replicate_message():
    data = request.json
    message = data['message']
    time.sleep(2)
    replicated_messages.append(message)
    return 'Message replicated', 200

@app.route('/messages', methods = ['GET'])
def get_replicated_messages():
    return jsonify(replicated_messages)

def run_server():
    app.run(host = '0.0.0.0', port=5001)

if __name__ == '__main__':
    app.debug = True
    run_server()
