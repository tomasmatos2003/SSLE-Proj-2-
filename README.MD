### How to run

#### 1
python3 registry.py 

#### 2 
##### (option 1)
Vulneable to node failures and bizantines

python3 vulnerable/bank_node.py 5001

python3 vulnerable/bank_node.py 5002 -m  (malicious)

python3 vulnerable/bank_node.py 5003

##### (option 2)  
Using paxos to deal with node fails

python3 good_paxos/bank_node.py 5001

python3 good_paxos/bank_node.py 5002 -m  (malicious)

python3 good_paxos/bank_node.py 5003

##### (option 3)  
Using pbft to deal with node fails and byzantine npdes

python3 good_pbft/bank_node.py 5001

python3 good_pbft/bank_node.py 5002 -m  (malicious)

python3 good_pbft/bank_node.py 5003


#### 3 - Test
python3 check_nodes.py