from flask import Flask, jsonify, request

app = Flask(__name__)

nodes = []
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
