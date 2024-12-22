from flask import Flask, jsonify, request
import requests
import threading
import time

app = Flask(__name__)

nodes = []

def health_check():
    global nodes
    while True:
        to_rm = []
        for node in nodes:
            try:
                response = requests.get(node + "/health", timeout=5)
                if response.status_code != 200:
                    to_rm.append(node)
            except requests.exceptions.RequestException:
                to_rm.append(node)

        nodes = [n for n in nodes if n not in to_rm]
        time.sleep(10) 

@app.route('/nodes', methods=['GET'])
def get_nodes():
    return jsonify(nodes)

@app.route('/node', methods=['POST'])
def add_node():
    data = request.form.to_dict()
    node = data["url"]

    if node in nodes:
        return jsonify(node), 409

    nodes.append(node)
    return jsonify(nodes), 201

if __name__ == '__main__':
    health_check_thread = threading.Thread(target=health_check, daemon=True)
    health_check_thread.start()

    app.run(host='0.0.0.0', port=5000)
