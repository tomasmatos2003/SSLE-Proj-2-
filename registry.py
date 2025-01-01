from flask import Flask, jsonify, request
import requests
import threading
import time

app = Flask(__name__)

nodes = []

# def health_check():
#     global nodes
#     while True:
#         to_rm = []
#         for node in nodes:
#             try:
#                 response = requests.get(node + "/health", timeout=5)
#                 if response.status_code != 200:
#                     to_rm.append(node)
#             except requests.exceptions.RequestException:
#                 to_rm.append(node)

#         nodes = [n for n in nodes if n not in to_rm]
#         time.sleep(30) 

reputations = {}
bizantines = []

@app.route('/reputations', methods=['GET'])
def get_repu():
    return jsonify(reputations)

@app.route('/nodes', methods=['GET'])
def get_nodes():
    filtered_nodes = [node for node in nodes if node not in bizantines]
    return jsonify(filtered_nodes)

@app.route('/bizantines', methods=['GET'])
def get_bizantines():
    return jsonify(bizantines)

@app.route('/node', methods=['POST'])
def add_node():
    data = request.form.to_dict()
    node = data["url"]

    if node in bizantines:
        bizantines.remove(node)

    if node in nodes:
        return jsonify(node), 409

    nodes.append(node)
    return jsonify(nodes), 201


@app.route('/rm_node', methods=['POST'])
def rm_node():
    data = request.form.to_dict()
    node = data["url"]

    if node in nodes:
        nodes.remove(node)
        return jsonify(node), 200

    return jsonify(nodes), 409

def check_bizantines(reputations):
    print("--> ", reputations)
    suspected_byzantine_nodes = []

    dic = {node : [] for node in reputations.keys()}

    for node in reputations.keys():
        for n in reputations[node].keys():
            if n not in dic:
                dic[n] = []
            dic[n].append(reputations[node][n])

    print("DALE", dic)

    for node in dic.keys():
        int_scores = [int(score) for score in dic[node]]
        if len(int_scores) == len(nodes) - 1:
            
            average_score = sum(int_scores) / len(int_scores)
            if average_score < 20:
                suspected_byzantine_nodes.append(node)

    return suspected_byzantine_nodes

@app.route('/update_reputation', methods=['POST'])
def update_reputation():
    global bizantines

    data = request.form.to_dict()
    node = data.pop("node", None)
    reputations[node] = data

    bizantines = check_bizantines(reputations)

    return jsonify(nodes), 200

if __name__ == '__main__':
    # health_check_thread = threading.Thread(target=health_check, daemon=True)
    # health_check_thread.start()

    app.run(host='0.0.0.0', port=5000)
