from flask import Flask, request, jsonify
import threading
import uuid
import requests
import logging
import time
from venv import logger

app = Flask(__name__)
messages = []
message_ids = set()
message_texts = set()
SECONDARY_SERVERS = ['http://secondary1:5001', 'http://secondary2:5001']
messages_lock = threading.Lock()

secondary_status = {secondary: "Healthy" for secondary in SECONDARY_SERVERS}
heartbeat_interval = 5 # Heartbeat check interval in seconds
retry_delay = 5 # Initial retry delay in seconds
quorum = len(SECONDARY_SERVERS) // 2  + 1 # Define the quorum

is_read_only = threading.Event() # Event to signal read-only mode
is_read_only.clear()

@app.route('/log', methods=['POST'])
def add_message():
    global messages, message_ids, message_texts

    if is_read_only.is_set():
        return "Master is in read-only mode due to insufficient quorum", 503

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
    #acks_lock = threading.Lock()
    duplicates_detected = False

    def replicate_to_secondary(secondary):
        nonlocal acks, duplicates_detected
        success = replicate_message(message, message_id, secondary)
        if success:
            acks +=1
        else:
            duplicates_detected = True

    threads = []

    for secondary in SECONDARY_SERVERS:
        if secondary_status[secondary] == "Healthy":
            thread = threading.Thread(target=replicate_to_secondary, args=(secondary,))
            threads.append(thread)
            thread.start()
        elif secondary_status[secondary] != "Unhealthy":
            # Retry with suspected secondaries
            thread = threading.Thread(target=replicate_to_secondary, args=(secondary,))
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

@app.route('/health', methods=['GET'])
def health_status():
    return jsonify(secondary_status)

def replicate_message(message, message_id, secondary):
    #nonlocal acks, duplicates_detected
    retry_attempts = 0
    while True:
        try:
            response = requests.post(f"{secondary}/replicate", json={"message_id": message_id, "message": message})
            if response.status_code == 200:
                return True
            elif response.status_code == 400:
                return False
        except Exception as e:
            logging.error(f"Replication failed to {secondary}: {e}")

        retry_attempts += 1
        time.sleep(min(retry_delay*(2**retry_attempts), 60))  # Cap the sleep time to 60 seconds

def heartbeat():
    global secondary_status
    while True:
        healthy_count = 0
        for secondary in SECONDARY_SERVERS:
            try:
                response = requests.get(f"{secondary}/health")
                if response.status_code == 200:
                    secondary_status[secondary] = "Healthy"
                    healthy_count += 1
            except:
                if secondary_status[secondary] == "Healthy":
                    secondary_status[secondary] = "Suspected"
                elif secondary_status[secondary] == "Suspected":
                    secondary_status[secondary] = "Unhealthy"

        if healthy_count >= quorum:
            is_read_only.clear()
        else:
            is_read_only.set()

        time.sleep(heartbeat_interval)


def replicate_lost_messages():
    global messages
    while True:
        for secondary in SECONDARY_SERVERS:
            if secondary_status[secondary] == "Healthy":
                for message in messages:
                    replicate_message(message['message'], message['message_id'], secondary)
        time.sleep(60)

def run_server():
    print("Starting server")
    app.run(host='0.0.0.0', port=5000)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=replicate_lost_messages, daemon=True).start()
    threading.Thread(target=heartbeat, daemon=True).start()
    app.debug = True
    run_server()
