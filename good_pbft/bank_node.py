from flask import Flask, jsonify, request
import sys
import requests
from account import Account
import threading
import uuid 
import time
import random
import hashlib
import json 
from collections import Counter

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
reputation = {}
quorum_size = 0


@app.route('/health', methods=['GET'])
def get_health():
    return jsonify(), 200

@app.route('/newNode', methods=['POST'])
def addnode():
    global nodes, reputation
    
    data = request.form.to_dict()
    url = data["url"]

    if url in nodes:
        return jsonify({"status": "rejected"}), 400

    nodes.append(url)
    reputation[url] = 100

    print(nodes)
    return jsonify({"status": "accepted"}), 200


@app.route('/accounts', methods=['GET'])
def get_accounts():
    accounts_list = [account.to_dict() for account in accounts]
    return jsonify(accounts_list), 200

@app.route('/reputations', methods=['GET'])
def get_reputations():
    return jsonify(reputation), 200


def broadcast_to_nodes(endpoint, data):
    """Broadcast a message to all registered nodes concurrently."""
    global nodes, thisnode
    
    data["node"] = thisnode

    if is_malicious:
        data["amount"] = random.randint(0, 1000)
    

    def send_request(node):
        delay = random.uniform(0, 1)
        try:
            time.sleep(delay)
            requests.post(node + endpoint, data=data)
        except Exception as e:
            print(f"Failed to contact node {node}: {e}")
            nodes.remove(node)
            # requests.post(registry + "/rm_node", data={"url": node})

    threads = []
    for node in nodes:
        rep = reputation[node]
        if rep < 20:
            continue

        thread = threading.Thread(target=send_request, args=(node,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    

@app.route('/preprepare', methods=['POST'])
def preprepare():
    """PBFT Pre-Prepare Phase."""
    global preprepared_messages, is_malicious, thisnode

    if 'preprepared_messages' not in globals():
        preprepared_messages = {}

    data = request.form.to_dict()

    operation = data["operation"]        
    message_id = data["message_id"] 
    
    request_digest = data.pop("digest", None)
    recv_node = data.pop("node", None) 
    serialized_data = json.dumps(data, sort_keys=True) 
    digest = hashlib.sha256(serialized_data.encode()).hexdigest()
    data["digest"] = digest

    if request_digest != digest:
        print("LOWER THE REPUTATION preprepare ", recv_node)
        reputation[recv_node] -= 25
    # else:
    #     print("ALL OK " )

    if reputation[recv_node] < 20:
        return jsonify({"status": "rejected"}), 400
        

    print(f"[Pre-Prepare] Received operation: {operation} from {recv_node}")
    
    
    if message_id not in preprepared_messages:
        preprepared_messages[message_id] = []

    data_copy = data.copy()
    data_copy["node"] = recv_node
    preprepared_messages[message_id].append(data_copy)

    if message_id not in prepared_messages:
        prepared_messages[message_id] = []

    time.sleep(2) #ensure receiving

    broadcast_to_nodes("/prepare", data)
    
    return jsonify({"status": "accepted"}), 200


def checkDigests(message_id):
    trust_factors = {}  # Dictionary to store trust factors for each digest
    overall_counts = Counter()  # Aggregate digest counts across all phases
    digest_details = {}  # Dictionary to store digest details (count, nodes, owner, amount)
    majority_digests = {}  # Majority digest for each phase

    def resolve_conflict(digest, amount1, message):
        
        message.pop("digest", None)
        message.pop("node", None) 
        serialized_data = json.dumps(message, sort_keys=True) 
        digest_m = hashlib.sha256(serialized_data.encode()).hexdigest()

        if digest_m == digest:
            return message["amount"]
        
        message["amount"] = amount1
        serialized_data = json.dumps(message, sort_keys=True) 
        digest_a1 = hashlib.sha256(serialized_data.encode()).hexdigest()
        if digest_a1 == digest:
            return amount1
        
        return None



    def process_messages(phase_name, messages):
        """Helper function to process messages and compute trust factors."""
        digest_nodes = {}
        digest_owners = {}
        digest_amounts = {}

        for m in messages:
            digest = m["digest"]
            node = m["node"]
            owner = m["owner"]
            amount = m["amount"]

            if digest not in digest_nodes:
                digest_nodes[digest] = []
                digest_owners[digest] = None  # Single owner per digest
                digest_amounts[digest] = None  # Single amount per digest

            digest_nodes[digest].append(node)

            # Set the owner, ensuring consistency
            if digest_owners[digest] is None:
                digest_owners[digest] = owner
            elif digest_owners[digest] != owner:
                raise ValueError(f"Conflicting owners for digest {digest}: {digest_owners[digest]} vs {owner}")

            # Set the amount, ensuring consistency
            if digest_amounts[digest] is None:
                digest_amounts[digest] = amount
            elif digest_amounts[digest] != amount:
                # print(f"Conflict detected for digest {digest}: {digest_amounts[digest]} vs {amount}")
                mcpy = m.copy()
                correct_amount = resolve_conflict(digest, digest_amounts[digest], mcpy)
                digest_amounts[digest] = correct_amount
                # print(f"Resolved conflict for digest {digest}. Correct amount: {correct_amount}")

        # Count occurrences of each digest
        digest_counts = Counter({digest: len(nodes) for digest, nodes in digest_nodes.items()})
        overall_counts.update(digest_counts)
        
        # Find the majority digest for the current phase
        if digest_counts:
            majority_digest, majority_count = digest_counts.most_common(1)[0]
            majority_digests[phase_name] = (majority_digest, majority_count)
        else:
            majority_digests[phase_name] = None

        # Update trust factors and digest details
        for digest, nodes in digest_nodes.items():
            count = len(nodes)
            if digest not in trust_factors:
                trust_factors[digest] = 0
            trust_factors[digest] += count

            if digest not in digest_details:
                digest_details[digest] = (0, [], None, None)  # Initialize with placeholders
            digest_details[digest] = (
                digest_details[digest][0] + count,  # Total count
                digest_details[digest][1] + nodes,  # List of nodes
                digest_owners[digest],  # Single owner
                digest_amounts[digest],  # Single amount
            )

        # Debugging output
        # print(f"    [{phase_name.capitalize()}] Digest Details: {digest_nodes}")
        # print(f"    [{phase_name.capitalize()}] Majority Digest: {majority_digest if digest_counts else 'None'} with count {majority_count if digest_counts else 0}")

    # Process each phase
    if message_id in preprepared_messages:
        process_messages("preprepared", preprepared_messages[message_id])
    if message_id in prepared_messages:
        process_messages("prepared", prepared_messages[message_id])
    if message_id in committed_messages:
        process_messages("committed", committed_messages[message_id])

    # Find the overall majority digest across all phases
    if overall_counts:
        overall_majority_digest, overall_majority_count = overall_counts.most_common(1)[0]
    else:
        overall_majority_digest, overall_majority_count = None, 0

    # Sort digest details by count (ascending)
    sorted_digest_details = dict(sorted(digest_details.items(), key=lambda item: item[1][0]))

    # Debugging output
    # print(f"Overall Majority Digest: {overall_majority_digest} with count {overall_majority_count}")
    # print(f"Trust Factors: {trust_factors}")
    # print(f"Sorted Digest Details: {sorted_digest_details}")
    
    return sorted_digest_details, overall_majority_count  # Return sorted dictionary

@app.route('/prepare', methods=['POST'])
def prepare():
    global prepared_messages, nodes, is_malicious, thisnode, preprepared_messages
    """PBFT Prepare Phase."""

    data = request.form.to_dict()
    operation = data["operation"]
    message_id = data["message_id"]

    request_digest = data.pop("digest", None)
    recv_node = data.pop("node", None) 

    serialized_data = json.dumps(data, sort_keys=True) 
    digest = hashlib.sha256(serialized_data.encode()).hexdigest()
    data["digest"] = request_digest
    
    if request_digest != digest:
        print("LOWER THE REPUTATION prepare  ", recv_node)
        reputation[recv_node] -= 25
    # else:
    #     print("ALL OK")

    print(f"[Prepare] Received operation: {operation} from {recv_node} data: {data}")
    
    data["node"] = recv_node

    n = len(nodes)  
    b = n // 3
    quorum_size = n - b
    # print("QUORUM ", quorum_size)
    
    if message_id in prepared_messages:
        prepared_messages[message_id].append(data)

    trust_factors, max_count = checkDigests(message_id)
    # print("trust ", trust_factors)
    # exclude the last because it is the majority
    # print("MAX ", max_count)

    datacopy = data.copy()

    if message_id not in preprepared_messages.keys() :

        # print("SOU O PROPOSER")
            
        if message_id in prepared_messages and len(prepared_messages[message_id]) == quorum_size + 1:
          
            if trust_factors:
            
                for hash in list(trust_factors.keys())[:-1]:
                    count = trust_factors[hash][0]
                    senders = trust_factors[hash][1]
                    if max_count > count and len(senders) == 1:
                        print("BAIXAR REPUTATION PREPARE ", senders[0])
                        bizanti_node = senders[0]
                        reputation[bizanti_node] -= 25

                greater_hash = list(trust_factors.keys())[-1]
                new_owner = trust_factors[greater_hash][2]
                new_amount = trust_factors[greater_hash][3]
                
                # print(f"Major Hash: {greater_hash}, New Owner: {new_owner}, New Amount: {new_amount}")

                datacopy['owner'] = new_owner
                datacopy['amount'] = new_amount

            # print("COMMIT " , datacopy)
            time.sleep(2) #ensure receiving
          
            broadcast_to_nodes("/commit", datacopy)
                
            return jsonify({"status": "prepared"}), 200
    # is a regular
    elif len(preprepared_messages[message_id]) == 1: 
        # print("SOU UM NORMAL")
       
        if message_id in prepared_messages and len(prepared_messages[message_id]) == quorum_size:
          
            if trust_factors:
        
                for hash in list(trust_factors.keys())[:-1]:
                    count = trust_factors[hash][0]
                    senders = trust_factors[hash][1]
                    if max_count > count and len(senders) == 1:
                        print("BAIXAR REPUTATION PREPARE ", senders[0])
                        bizanti_node = senders[0]
                        reputation[bizanti_node] -= 25

                greater_hash = list(trust_factors.keys())[-1]
                new_owner = trust_factors[greater_hash][2]
                new_amount = trust_factors[greater_hash][3]
                
                # print(f"Major Hash: {greater_hash}, New Owner: {new_owner}, New Amount: {new_amount}")

                datacopy['owner'] = new_owner
                datacopy['amount'] = new_amount

            # print("COMMIT " , datacopy)

            time.sleep(2) #ensure receiving

            broadcast_to_nodes("/commit", datacopy)
                
            return jsonify({"status": "prepared"}), 200

    print(f"[Prepare] Consensus not yet achieved for operation: {operation} from {data['node']}")
    return jsonify({"status": "rejected"}), 400


@app.route('/commit', methods=['POST'])
def commit():
    """PBFT Commit Phase."""
    global committed_messages, nodes, is_malicious
    
    data = request.form.to_dict()
    operation = data["operation"]
    message_id = data["message_id"]

    request_digest = data.pop("digest", None)
    recv_node = data.pop("node", None) 

    serialized_data = json.dumps(data, sort_keys=True) 
    digest = hashlib.sha256(serialized_data.encode()).hexdigest()
    data["digest"] = request_digest


    if request_digest != digest:
        print("LOWER THE REPUTATION commit ", recv_node , " data ", serialized_data, " digest ", digest, " req_digest ", request_digest)
        reputation[recv_node] -= 25

    print(f"[Commit] Received operation: {operation} from {recv_node}, data {data}")
    
    data["node"] = recv_node

    if message_id not in committed_messages:
        committed_messages[message_id] = []
    
    committed_messages[message_id].append(data)  # SOLVEE here - change operation to an req id []

    trust_factors, max_count = checkDigests(message_id)

    n = len(nodes)  
    b = n // 3
    quorum_size = n - b

    if message_id in committed_messages and len(committed_messages[message_id]) == quorum_size:
        

        if trust_factors:
            
            for hash in list(trust_factors.keys())[:-1]:
                count = trust_factors[hash][0]
                senders = trust_factors[hash][1]
                if max_count > count and len(senders) == 1:
                    print("BAIXAR REPUTATION COMMIT ", senders[0])
                    bizanti_node = senders[0]
                    reputation[bizanti_node] -= 25
                
            greater_hash = list(trust_factors.keys())[-1]  # Safely access the last key
            new_owner = trust_factors[greater_hash][2] # Get the new owner
            new_amount = trust_factors[greater_hash][3]  # Get the new amount

            # print(f"Major Hash: {greater_hash}, New Owner: {new_owner}, New Amount: {new_amount}")
            
            data['owner'] = new_owner
            data['amount'] = new_amount

        # print("EXECUTAR")
        execute_operation(data)
                
        return jsonify({"status": "committed"}), 200

    print(f"[Commit] Consensus not yet achieved for operation: {operation} from {data['node']}")
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
    global prepared_messages, is_malicious

    data = request.form.to_dict()

    message_id = str(uuid.uuid4())
    data["message_id"] = message_id 
    
    prepared_messages[message_id] = []

    print(f"[Create Account] Request received: {data}")
    if int(data.get("consenso", 0)) == 1:
        data["operation"] = "create_account"

        serialized_data = json.dumps(data, sort_keys=True) 
        digest = hashlib.sha256(serialized_data.encode()).hexdigest()
        data["digest"] = digest

        broadcast_to_nodes("/preprepare", data)
    else:
        create_account_internal(data)

    return jsonify({"status": "initiated"}), 201


@app.route('/deposit', methods=['POST'])
def deposit():
    """Public endpoint to deposit into an account."""
    global prepared_messages, is_malicious

    data = request.form.to_dict()
    
    message_id = str(uuid.uuid4())
    data["message_id"] = message_id 
    prepared_messages[message_id] = []

    print(f"[Deposit] Request received from: {data}")
    if int(data.get("consenso", 0)) == 1:
        data["operation"] = "deposit"

        serialized_data = json.dumps(data, sort_keys=True) 
        digest = hashlib.sha256(serialized_data.encode()).hexdigest()
        data["digest"] = digest

        broadcast_to_nodes("/preprepare", data)
    else:
        deposit_internal(data)

    return jsonify({"status": "initiated"}), 200


@app.route('/withdraw', methods=['POST'])
def withdraw():
    """Public endpoint to withdraw from an account."""
    global prepared_messages, is_malicious, thisnode

    data = request.form.to_dict()

    message_id = str(uuid.uuid4())
    data["message_id"] = message_id 
    prepared_messages[message_id] = []

    print(f"[Withdraw] Request received from: {data}")
    if int(data.get("consenso", 0)) == 1:
        data["operation"] = "withdraw"

        serialized_data = json.dumps(data, sort_keys=True) 
        digest = hashlib.sha256(serialized_data.encode()).hexdigest()
        data["digest"] = digest

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

    thisnode = f"http://{incus_ip}:{port}"
    response = requests.post(registry + "/node", data={"url": f"http://{incus_ip}:{port}"})
    
    nodes_ = requests.get(registry + "/nodes").json()
    nodes = [node for node in nodes_ if port not in node]
    reputation = {n:100 for n in nodes}

    for node in nodes:
        requests.post(node + "/newNode", data={"url": f"http://{incus_ip}:{port}"})

    app.run(host='0.0.0.0', port=port)
