from http.client import HTTPException
from venv import logger

from flask import Flask, request, jsonify
import requests
import logging

import os

app = Flask(__name__)
messages = []
SECONDARY_SERVERS = [('secondary1', 5001), ('secondary2', 5001)]
#SECONDARY_SERVERS = [('secondary1', 5001)]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route('/log', methods=['POST'])
def append_messages():
    print ("Entering append_messages")
    data = request.json
    message = data['message']
    print ("Sending")
    messages.append(message)
    logger.info(f"Message '{message}' append to primary")

    # Replicating the message to all secondary servers
    logger.info("About to start replication")
    for secondary in SECONDARY_SERVERS:
        logger.info("Trying to connect to secondary server")

        secondary_host, secondary_port = secondary

        url = f"http://{secondary_host}:{secondary_port}/replicate"
        logger.info(f"{secondary_host} and {secondary_port}")
        response = requests.post(url, json={'message': message})
        logger.info(f"{response.text}")

        if response.status_code != 200:
            return response.text, 500

    logger.info(f"Messages sent to all servers")
    return 'Message appended and replicated', 200


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
