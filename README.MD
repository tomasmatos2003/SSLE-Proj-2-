### How to run

#### 1
python3 registry.py 

#### 2 
##### (option 1)
python3 vulnerable/bank_node.py 5001

python3 vulnerable/bank_node.py 5002 -m  (malicious)

python3 vulnerable/bank_node.py 5003

##### (option 2) - paxos

python3 good/bank_node.py 5001

python3 good/bank_node.py 5002 -m  (malicious)

python3 good/bank_node.py 5003

#### 3 - Test
python3 check_nodes.py