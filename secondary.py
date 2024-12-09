import logging
from random import random

from flask import Flask, request, jsonify
import time
import threading
import random

app = Flask(__name__)
replicated_messages = []
message_ids = set()
message_texts = set()
lock = threading.Lock()


@app.route('/replicate', methods=['POST'])
def replicate_message():
    data = request.json
    message = data['message']
    message_id = data['message_id']

    if not message or not message_id:
        return "Message and Message ID are required", 400

    with lock:
        if message_id in message_ids or message in message_texts:
            return "Message already exists", 400

        if random.random() < 0.1:
            return "Internal Server Error", 500

        time.sleep(5)

        # # Maintain order - ensure previous messages are received first
        # expected_message_id = len(replicated_messages) + 1
        # start = time.perf_counter()
        # while not (str(expected_message_id) in message_ids or time.perf_counter() - start > 60):
        #     time.sleep(1)

        # Add message to the secondary server
        replicated_messages.append({"message_id": message_id, "message": message})
        message_ids.add(message_id)
        message_texts.add(message)

    return "Message replicated", 200


@app.route('/messages', methods = ['GET'])
def get_replicated_messages():
    return jsonify(replicated_messages)

@app.route('/health', methods = ['GET'])
def health_check():
    return "Healthy", 200

def run_server():
    app.run(host = '0.0.0.0', port=5001)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.debug = True
    run_server()
