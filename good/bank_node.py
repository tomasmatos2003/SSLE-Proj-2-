from flask import Flask, jsonify, request
import sys
import requests
from account import Account
import random
import threading

app = Flask(__name__)

accounts = []
registry = "http://0.0.0.0:5000"
incus_ip = "0.0.0.0"
is_malicious = False

# Paxos state
proposal_number = 0
accepted_proposal = None
accepted_value = None
learned_value = None
votes = 0
quorum_size = 0

@app.route('/health', methods=['GET'])
def get_health():
    return jsonify(), 200

@app.route('/accounts', methods=['GET'])
def get_accounts():
    accounts_list = [account.to_dict() for account in accounts]
    return jsonify(accounts_list), 200

# Paxos Proposer - Initiate Consensus
def paxos_propose(endpoint, data):
    global proposal_number, accepted_proposal, votes, quorum_size

    proposal_number += 1
    votes = 0  # Reset vote count

    print(f"[Propose] Starting proposal {proposal_number} for endpoint {endpoint}")

    response = requests.get(registry + "/nodes")
    nodes = response.json()
    nodes = [node for node in nodes if port not in node]
    quorum_size = len(nodes) // 2 + 1  # Majority required for consensus

    print(f"[Propose] Quorum size calculated as {quorum_size}")
    print(f"[Propose] Nodes participating: {nodes}")

    # Prepare Phase
    for node in nodes:
        try:
            resp = requests.post(node + "/paxos/prepare", json={
                "proposal_number": proposal_number,
                "data": data
            })
            if resp.status_code == 200:
                print(f"[Prepare] Node {node} accepted proposal {proposal_number}")
                votes += 1
            else:
                print(f"[Prepare] Node {node} rejected proposal {proposal_number}")
        except Exception as e:
            print(f"[Prepare] Node {node} unreachable: {e}")

    print(f"[Prepare] Votes received: {votes}/{len(nodes)}")

    # Check if quorum reached
    if votes >= quorum_size:
        print("[Propose] Quorum reached in Prepare phase.")
        # Accept Phase
        votes = 0  # Reset vote count
        for node in nodes:
            try:
                resp = requests.post(node + "/paxos/accept", json={
                    "proposal_number": proposal_number,
                    "data": data
                })
                if resp.status_code == 200:
                    print(f"[Accept] Node {node} accepted proposal {proposal_number}")
                    votes += 1
                else:
                    print(f"[Accept] Node {node} rejected proposal {proposal_number}")
            except Exception as e:
                print(f"[Accept] Node {node} unreachable: {e}")

        print(f"[Accept] Votes received: {votes}/{len(nodes)}")

        # Check if quorum reached for acceptance
        if votes >= quorum_size:
            print("[Propose] Quorum reached in Accept phase. Committing value.")
            # Commit phase
            for node in nodes:
                try:
                    requests.post(node + endpoint, data=data)
                    print(f"[Commit] Value committed to node {node}")
                except Exception as e:
                    print(f"[Commit] Node {node} unreachable: {e}")
        else:
            print("[Propose] Quorum not reached in Accept phase.")
    else:
        print("[Propose] Quorum not reached in Prepare phase.")

@app.route('/paxos/prepare', methods=['POST'])
def paxos_prepare():
    global proposal_number, accepted_proposal, accepted_value

    data = request.json
    incoming_proposal = data["proposal_number"]

    print(f"[Prepare] Received proposal {incoming_proposal}. Current proposal: {proposal_number}")

    if incoming_proposal > proposal_number:
        proposal_number = incoming_proposal
        print(f"[Prepare] Proposal {incoming_proposal} accepted.")
        return jsonify({"status": "accepted"}), 200
    print(f"[Prepare] Proposal {incoming_proposal} rejected.")
    return jsonify({"status": "rejected"}), 400

@app.route('/paxos/accept', methods=['POST'])
def paxos_accept():
    global proposal_number, accepted_proposal, accepted_value

    data = request.json
    incoming_proposal = data["proposal_number"]
    incoming_value = data["data"]

    print(f"[Accept] Received proposal {incoming_proposal}. Current proposal: {proposal_number}")

    if incoming_proposal >= proposal_number:
        proposal_number = incoming_proposal
        accepted_proposal = incoming_proposal
        accepted_value = incoming_value
        print(f"[Accept] Proposal {incoming_proposal} accepted.")
        return jsonify({"status": "accepted"}), 200
    print(f"[Accept] Proposal {incoming_proposal} rejected.")
    return jsonify({"status": "rejected"}), 400

@app.route('/create_account', methods=['POST'])
def create_account():
    data = request.form.to_dict()
    print(f"[Create Account] Request received: {data}")
    owner = data["owner"]
    amount = float(data.get("amount", 0))

    if any(account.owner == owner for account in accounts):
        print("[Create Account] Account already exists.")
        return jsonify({"error": "Account already exists for this owner"}), 409

    account = Account(amount, owner)
    accounts.append(account)

    print(f"[Create Account] Account created: {account}")

    if int(data.get("consenso", 0)) == 1:
        data["consenso"] = "0"
        paxos_propose("/create_account", data)

    return jsonify({"owner": account.owner, "balance": account.balance}), 201

@app.route('/deposit', methods=['POST'])
def deposit():
    data = request.form.to_dict()
    print(f"[Deposit] Request received: {data}")
    owner = data["owner"]
    amount = float(data.get("amount", 0))

    account = next((acc for acc in accounts if acc.owner == owner), None)
    if not account:
        print("[Deposit] Account not found.")
        return jsonify({"error": "Account does not exist for this owner"}), 404

    account.deposit(amount)
    print(f"[Deposit] Updated account: {account}")

    if int(data.get("consenso", 0)) == 1:
        data["consenso"] = "0"
        paxos_propose("/deposit", data)

    return jsonify({"owner": account.owner, "balance": account.balance}), 200

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.form.to_dict()
    print(f"[Withdraw] Request received: {data}")
    owner = data["owner"]
    amount = float(data.get("amount", 0))

    account = next((acc for acc in accounts if acc.owner == owner), None)
    if not account:
        print("[Withdraw] Account not found.")
        return jsonify({"error": "Account does not exist for this owner"}), 404

    if account.withdraw(amount):
        print(f"[Withdraw] Updated account: {account}")
        if int(data.get("consenso", 0)) == 1:
            data["consenso"] = "0"
            paxos_propose("/withdraw", data)
        return jsonify({"owner": account.owner, "balance": account.balance}), 200

    print("[Withdraw] Insufficient funds.")
    return jsonify({"error": "Insufficient funds"}), 400

if __name__ == '__main__':
    port = str(sys.argv[1])

    if len(sys.argv) == 3 and str(sys.argv[2]) == "-m":
        is_malicious = True
        print("Running in malicious mode...")

    response = requests.post(registry + "/node", data={
        "url": f"http://{incus_ip}:{port}"
    })

    print(f"Node registered at {registry}/node with URL http://{incus_ip}:{port}")
    app.run(host='0.0.0.0', port=port)
