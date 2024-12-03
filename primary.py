from venv import logger

from flask import Flask, request, jsonify
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed


import os

app = Flask(__name__)
messages = []
SECONDARY_SERVERS = ['http://secondary1:5001', 'http://secondary2:5001']
#SECONDARY_SERVERS = [('secondary1', 5001), ('secondary2', 5001)]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def replicate_message_to_secondary(secondary_url, message):
    try:
        response = requests.post(f"{secondary_url}/replicate", json={"message": message}, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logging.error(f"Failed to replicate to {secondary_url}: {e}")
        return False

@app.route("/log", methods = ["POST"])
def append_message():
    message = request.json
    messages.append(message)
    logging.info(f"Message {message} appended to primary")

    # Replicate the message to secondary in parallel
    with ThreadPoolExecutor(max_workers=len(SECONDARY_SERVERS)) as executor:
        future_to_secondary = {executor.submit(replicate_message_to_secondary, secondary, message): secondary for secondary in SECONDARY_SERVERS}

        results = {}
        for future in as_completed(future_to_secondary):
            secondary = future_to_secondary[future]
            try:
                results[secondary] = future.result()
            except Exception as e:
                logging.error(f"exception raised during replication to {secondary}: {e}")
                results[secondary] = False

    if all(results.values()):
        return jsonify({"message": "Message appended and replicated to all secondaries"})
    else:
        messages.remove(message)
        failure_msgs = [
            f"{secondary}: {'Success' if status else 'Failed'}" for secondary, status in results.items()
        ]
        logging.error(f"Replication failed for message: {message}")
        return jsonify({"error": f"Replication for some or all secondaries failed: {failure_msgs}"}), 500




# @app.route('/log', methods=['POST'])
# def append_messages():
#     print ("Entering append_messages")
#     data = request.json
#     message = data['message']
#     print ("Sending")
#     messages.append(message)
#     logger.info(f"Message '{message}' append to primary")
#
#     # Replicating the message to all secondary servers
#     logger.info("About to start replication")
#     for secondary in SECONDARY_SERVERS:
#         logger.info("Trying to connect to secondary server")
#
#         secondary_host, secondary_port = secondary
#
#         url = f"http://{secondary_host}:{secondary_port}/replicate"
#         logger.info(f"{secondary_host} and {secondary_port}")
#         response = requests.post(url, json={'message': message})
#         logger.info(f"{response.text}")
#
#         if response.status_code != 200:
#             return response.text, 500
#
#     logger.info(f"Messages sent to all servers")
#     return 'Message appended and replicated', 200
#

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
