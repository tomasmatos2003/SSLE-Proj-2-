
from flask import Flask, jsonify, request
import sys
import requests
from account import Account
import random

app = Flask(__name__)

accounts = []

registry = "http://0.0.0.0:5000"

incus_ip = "0.0.0.0"

is_malicious = False

@app.route('/health', methods=['GET'])
def get_health():
    return jsonify(), 200

@app.route('/accounts', methods=['GET'])
def get_accounts():
    accounts_list = [account.to_dict() for account in accounts]
    return jsonify(accounts_list), 200

def ensure_consenso(endpoint,data):

    response = requests.get(registry+"/nodes")
    nodes = response.json()
    nodes = [node for node in nodes if port not in node]
    
    for node in nodes:
        if is_malicious:
            data["amount"] = random.randint(0, 1000)

        requests.post(node+endpoint, data=data)

@app.route('/create_account', methods=['POST'])
def create_account():
    data = request.form.to_dict()
    owner = data["owner"]
    amount = float(data.get("amount", 0))
    consenso = int(data["consenso"])

    if any(account.owner == owner for account in accounts):
        return jsonify({"error": "Account already exists for this owner"}), 409

    account = Account(amount, owner)
    accounts.append(account)

    if consenso == 1:
        data["consenso"] = "0"
        ensure_consenso("/create_account", data)

    return jsonify({"owner": account.owner, "balance": account.balance}), 201

@app.route('/deposit', methods=['POST'])
def deposit():
    data = request.form.to_dict()
    owner = data["owner"]
    amount = float(data.get("amount", 0))
    consenso = int(data["consenso"])

    account = next((acc for acc in accounts if acc.owner == owner), None)
    if not account:
        return jsonify({"error": "Account does not exist for this owner"}), 404

    account.deposit(amount)

    if consenso == 1:
        data["consenso"] = "0"
        ensure_consenso("/deposit", data)

    return jsonify({"owner": account.owner, "balance": account.balance}), 200

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.form.to_dict()
    owner = data["owner"]
    amount = float(data.get("amount", 0)) 
    consenso = int(data["consenso"])

    account = next((acc for acc in accounts if acc.owner == owner), None)
    if not account:
        return jsonify({"error": "Account does not exist for this owner"}), 404
        
    if account.withdraw(amount):

        if consenso == 1:
            data["consenso"] = "0"
            ensure_consenso("/withdraw", data)
        
        return jsonify({"owner": account.owner, "balance": account.balance}), 200
    else:
        return jsonify({"error": "Insufficient funds"}), 400

if __name__ == '__main__':
    port = str(sys.argv[1])

    if len(sys.argv) == 3:
        if str(sys.argv[2]) == "-m":
            is_malicious = True
            print("Running in malicious mode...")
        else:
            print("Usage: python3 good_pbft/bank_node.py <port> [-m]")
            sys.exit(1)


    response = requests.post(registry+"/node", data={
            "url": "http://" + incus_ip + ":" + port
    })
    
    app.run(host='0.0.0.0', port=port)