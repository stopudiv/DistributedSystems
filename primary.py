import threading
import uuid
from venv import logger

from flask import Flask, request, jsonify
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import os

app = Flask(__name__)
messages = []
message_ids = set()
message_texts = set()
SECONDARY_SERVERS = ['http://secondary1:5001', 'http://secondary2:5001']
messages_lock = threading.Lock()

@app.route('/log', methods=['POST'])
def add_message():
    global messages, message_ids, message_texts
    content = request.json
    message = content.get('message')
    message_id = content.get('message_id', str(uuid.uuid4()))
    write_concern = content.get('w', len(SECONDARY_SERVERS) + 1)

    if not message:
        return "Message is required", 400

    with messages_lock:
        if message_id in message_ids or message_id in message_texts:
            return jsonify(f"Message already exists"), 400

        messages.append({"message_id": message_id, "message": message})
        message_ids.add(message_id)
        message_texts.add(message)

    acks = 1
    acks_lock = threading.Lock()
    duplicates_detected = False

    def replicate_message(message, message_id, secondary):
        nonlocal acks, duplicates_detected
        try:
            response = requests.post(f"{secondary}/replicate", json={"message_id": message_id, "message": message})
            if response.status_code == 200:
                with acks_lock:
                    acks += 1
            elif response.status_code == 400:
                duplicates_detected = True
        except Exception as e:
            logging.error(f"Acknowledgement failed from {secondary}: {e}")

    threads = []

    for secondary in SECONDARY_SERVERS:
        thread = threading.Thread(target=replicate_message, args = (message, message_id, secondary))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    if duplicates_detected:
        return "Duplicate message detected", 400
    elif acks >= int(write_concern):
        return "Message added successfully", 201
    else:
        return "Failed to meet write concern", 500

@app.route('/log', methods=['GET'])
def get_message():
    logger.info(f"Fetching messages")
    print("Fetching messages")
    return jsonify(messages)


def run_server():
    print("Starting server")
    app.run(host='0.0.0.0', port=5000)


if __name__ == "__main__":
    app.debug = True
    run_server()
