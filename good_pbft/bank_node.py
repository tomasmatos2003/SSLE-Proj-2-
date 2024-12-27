from flask import Flask, jsonify, request
import sys
import requests
from account import Account
import threading
import uuid 
import time
import random

app = Flask(__name__)

accounts = []
registry = "http://0.0.0.0:5000"
incus_ip = "0.0.0.0"
is_malicious = False

# PBFT State
preprepared_messages = {}
prepared_messages = {}
committed_messages = {}
nodes = []
quorum_size = 0


@app.route('/health', methods=['GET'])
def get_health():
    return jsonify(), 200

@app.route('/newNodes', methods=['POST'])
def addnode():
    global nodes
    
    data = request.form.to_dict()
    url = data["url"]

    if url in nodes:
        return jsonify({"status": "rejected"}), 400

    nodes.append(url)

    print(nodes)
    return jsonify({"status": "accepted"}), 200


@app.route('/accounts', methods=['GET'])
def get_accounts():
    accounts_list = [account.to_dict() for account in accounts]
    return jsonify(accounts_list), 200


def broadcast_to_nodes(endpoint, data):
    """Broadcast a message to all registered nodes concurrently."""
    global nodes
   
    print(nodes)

    def send_request(node):
        delay = random.uniform(0, 1)
        try:
            time.sleep(delay)
            requests.post(node + endpoint, data=data)
        except Exception as e:
            print(f"Failed to contact node {node}: {e}")
            # requests.post(registry + "/rm_node", data={"url": node})

    threads = []
    for node in nodes:
        thread = threading.Thread(target=send_request, args=(node,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    

@app.route('/preprepare', methods=['POST'])
def preprepare():
    """PBFT Pre-Prepare Phase."""
    global preprepared_messages

    if 'preprepared_messages' not in globals():
        preprepared_messages = {}

    data = request.form.to_dict()
    operation = data["operation"]
    client_ip = request.remote_addr
    message_id = data["message_id"] 

    if is_malicious:
        data["amount"] = random.randint(0, 1000)

    print(f"[Pre-Prepare] Received operation: {operation} from {client_ip}")
    
    if message_id not in preprepared_messages:
        preprepared_messages[message_id] = []

    preprepared_messages[message_id].append(client_ip)

    if message_id not in prepared_messages:
        prepared_messages[message_id] = []

    time.sleep(1) #ensure receiving

    broadcast_to_nodes("/prepare", data)
    return jsonify({"status": "accepted"}), 200


@app.route('/prepare', methods=['POST'])
def prepare():
    global prepared_messages, nodes
    """PBFT Prepare Phase."""

    data = request.form.to_dict()
    operation = data["operation"]
    client_ip = request.remote_addr
    message_id = data["message_id"]

    if is_malicious:
        data["amount"] = random.randint(0, 1000)

    print(f"[Prepare] Received operation: {operation} from {client_ip} data: {data}")
    print(nodes)
    n = len(nodes)  
    b = n // 3
    quorum_size = n - b
    
    if message_id in prepared_messages:
        prepared_messages[message_id].append(client_ip)
        print(len(prepared_messages[message_id]), quorum_size)

    print(prepared_messages)
    
    # is the proposer
    if message_id not in preprepared_messages.keys() :

        print("SOU O PROPOSER")
            
        if message_id in prepared_messages and len(prepared_messages[message_id]) == quorum_size:
            print("COMMIT")
            # print(f"[Prepare] Consensus achieved for operation: {operation} from {client_ip}")

            if message_id in prepared_messages:
                del prepared_messages[message_id] 

            time.sleep(1) #ensure receiving
            broadcast_to_nodes("/commit", data)
                
            return jsonify({"status": "prepared"}), 200
    # is a regular
    elif len(preprepared_messages[message_id]) == 1: 
        print("SOU UM NORMAL")
       
        if message_id in prepared_messages and len(prepared_messages[message_id]) >= quorum_size - 1:
            print("COMMIT")
            # print(f"[Prepare] Consensus achieved for operation: {operation} from {client_ip}")

            if message_id in preprepared_messages:
                del preprepared_messages[message_id] 

            if message_id in prepared_messages:
                del prepared_messages[message_id] 
                
            time.sleep(1) #ensure receiving
            broadcast_to_nodes("/commit", data)
                
            return jsonify({"status": "prepared"}), 200

    print(f"[Prepare] Consensus not yet achieved for operation: {operation} from {client_ip}")
    return jsonify({"status": "rejected"}), 400


@app.route('/commit', methods=['POST'])
def commit():
    """PBFT Commit Phase."""
    global committed_messages, nodes
    
    data = request.form.to_dict()
    operation = data["operation"]
    client_ip = request.remote_addr
    message_id = data["message_id"]

    if is_malicious:
        data["amount"] = random.randint(0, 1000)

    print(f"[Commit] Received operation: {operation} from {client_ip}")
    
    if message_id not in committed_messages:
        committed_messages[message_id] = []
    
    committed_messages[message_id].append(client_ip)  # SOLVEE here - change operation to an req id []

    n = len(nodes)  
    b = n // 3
    quorum_size = n - b

    print(len(committed_messages[message_id]) , quorum_size, quorum_size == len(committed_messages[message_id]))

    if message_id in committed_messages and len(committed_messages[message_id]) == quorum_size:

        print("EXECUTAR")
        execute_operation(data)
        if message_id in committed_messages:
            del committed_messages[message_id] 
        
        return jsonify({"status": "committed"}), 200

    print(f"[Commit] Consensus not yet achieved for operation: {operation} from {client_ip}")
    return jsonify({"status": "pending"}), 202

    

def execute_operation(data):
    """Execute the operation after Consenso."""
    operation = data["operation"]
    if operation == "create_account":
        create_account_internal(data)
    elif operation == "deposit":
        deposit_internal(data)
    elif operation == "withdraw":
        withdraw_internal(data)


def create_account_internal(data):
    """Internal function to create an account."""
    owner = data["owner"]
    amount = float(data.get("amount", 0))

    if any(account.owner == owner for account in accounts):
        print(f"[Create Account] Account already exists for {owner}.")
        return

    account = Account(amount, owner)
    accounts.append(account)
    print(f"[Create Account] Account created for {owner}: {account}")


def deposit_internal(data):
    """Internal function to deposit into an account."""
    owner = data["owner"]
    amount = float(data.get("amount", 0))

    account = next((acc for acc in accounts if acc.owner == owner), None)
    if not account:
        print(f"[Deposit] Account not found for {owner}.")
        return

    account.deposit(amount)
    print(f"[Deposit] Updated account for {owner}: {account}")


def withdraw_internal(data):
    """Internal function to withdraw from an account."""
    owner = data["owner"]
    amount = float(data.get("amount", 0))

    account = next((acc for acc in accounts if acc.owner == owner), None)
    if not account:
        print(f"[Withdraw] Account not found for {owner}.")
        return

    if not account.withdraw(amount):
        print(f"[Withdraw] Insufficient funds for {owner}.")
        return

    print(f"[Withdraw] Updated account for {owner}: {account}")


@app.route('/create_account', methods=['POST'])
def create_account():
    """Public endpoint to create an account."""
    global prepared_messages

    data = request.form.to_dict()
    client_ip = request.remote_addr
    message_id = str(uuid.uuid4())
    data["message_id"] = message_id 
    prepared_messages[message_id] = []

    if is_malicious:
        data["amount"] = random.randint(0, 1000)

    print(f"[Create Account] Request received from {client_ip}: {data}")
    if int(data.get("consenso", 0)) == 1:
        data["operation"] = "create_account"

        broadcast_to_nodes("/preprepare", data)
    else:
        create_account_internal(data)

    return jsonify({"status": "initiated"}), 201


@app.route('/deposit', methods=['POST'])
def deposit():
    """Public endpoint to deposit into an account."""
    global prepared_messages

    data = request.form.to_dict()
    client_ip = request.remote_addr
    message_id = str(uuid.uuid4())
    data["message_id"] = message_id 
    prepared_messages[message_id] = []

    if is_malicious:
        data["amount"] = random.randint(0, 1000)

    print(f"[Deposit] Request received from {client_ip}: {data}")
    if int(data.get("consenso", 0)) == 1:
        data["operation"] = "deposit"
        broadcast_to_nodes("/preprepare", data)
    else:
        deposit_internal(data)

    return jsonify({"status": "initiated"}), 200


@app.route('/withdraw', methods=['POST'])
def withdraw():
    """Public endpoint to withdraw from an account."""
    global prepared_messages

    data = request.form.to_dict()
    client_ip = request.remote_addr
    message_id = str(uuid.uuid4())
    data["message_id"] = message_id 
    prepared_messages[message_id] = []

    if is_malicious:
        data["amount"] = random.randint(0, 1000)

    print(f"[Withdraw] Request received from {client_ip}: {data}")
    if int(data.get("consenso", 0)) == 1:
        data["operation"] = "withdraw"
        broadcast_to_nodes("/preprepare", data)
    else:
        withdraw_internal(data)

    return jsonify({"status": "initiated"}), 200


if __name__ == '__main__':    
    port = str(sys.argv[1])

    if len(sys.argv) == 3:
        if str(sys.argv[2]) == "-m":
            is_malicious = True
            print("Running in malicious mode...")
        else:
            print("Usage: python3 good_pbft/bank_node.py <port> [-m]")
            sys.exit(1)

    response = requests.post(registry + "/node", data={"url": f"http://{incus_ip}:{port}"})
    
    nodes_ = requests.get(registry + "/nodes").json()
    nodes = [node for node in nodes_ if port not in node]

    for node in nodes:
        requests.post(node + "/newNodes", data={"url": f"http://{incus_ip}:{port}"})

    app.run(host='0.0.0.0', port=port)
