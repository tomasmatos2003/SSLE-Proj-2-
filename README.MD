### How to run

#### 1
python3 registry.py 

or

/registy_js do:

node -v
npm init -y  # Initializes a new Node.js project
npm install express
node app.jss

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


##### Test cases - good_pbft

4 nodes /w 1 bizantine

1. Make 2 transactions to the faulty node and verify reputation getting down, but unfortunaly the transaction happen with random values. 

(Restart the bizantine node, to reset the reputations)

2. Make transaction to a non faulty node and verify reputation getting down and transaction sucessfull in every node. 


4 nodes /w 2 bizantine

1. Make transactions to a node and verify reputation getting down, but unfortunaly the transaction happen with random values only in the first 2 transactions. 

7 nodes /w 2 bizantine

1.  Make 2 transactions to the faulty node and verify reputation getting down in both bizantines, but unfortunaly the transaction happen with random values. 


(Restart the bizantine node, to reset the reputations)

2. Make transaction to a non faulty node and verify reputation getting down and transaction sucessfull in every node. 



