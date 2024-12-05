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
    #time.sleep(2)
    if not message or not message_id:
        return "Message and Message ID are required", 400
    with lock:
        if message_id in message_ids or message in message_texts:
            return "Message already exists", 400

        time.sleep(5)

        replicated_messages.append({"message_id": message_id, "message": message})
        message_ids.add(message_id)
        message_texts.add(message)

    return "Message replicated", 200


@app.route('/messages', methods = ['GET'])
def get_replicated_messages():
    return jsonify(replicated_messages)

def run_server():
    app.run(host = '0.0.0.0', port=5001)

if __name__ == '__main__':
    app.debug = True
    run_server()
