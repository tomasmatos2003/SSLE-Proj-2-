import sys
import requests

def main_menu():
    while True:

        print("\n==== Nodes Application ====")
        print("1. Check nodes data")
        print("2. Add account")
        print("3. Withdraw from account")
        print("4. Deposit in account")
        print("5. Exit")
        choice = input("Choose an option (1-5): ")
        
        response = requests.get("http://0.0.0.0:5000/nodes")
        nodes = []
        if response.status_code == 200:
            nodes = response.json()

        if choice == "1":
            
            for node in nodes:
                print(" Node: " + node)

                r = requests.get(node + "/accounts")
                accounts = r.json()

                for account in accounts:
                    print("     ",account)

                print("")

        elif choice == "2":
            fnode = ""
            for node in nodes:
                resp = input("Insert in node: "+ node + " ? (y/N)")
                if resp.lower() == "y":
                    fnode = node
                    break

            if fnode == "":
                continue

            owner = input("     Owner:")
            amount = float(input("     Amount:"))

            response = requests.post(fnode+"/create_account", data={
                "owner":owner,
                "amount":str(amount),
                "consenso":"1"
            })

            print("     Result: ", response.status_code)

        elif choice == "3":
            fnode = ""
            for node in nodes:
                resp = input("Insert in node: " + node + " ? (y/N)")
                if resp.lower() == "y":
                    fnode = node
                    break

            if fnode == "":
                continue

            owner = input("     Owner:")
            amount = float(input("     Amount:"))

            response = requests.post(fnode+"/withdraw", data={
                "owner":owner,
                "amount":str(amount),
                "consenso":"1"
            })
            print("     Result: ", response.status_code)

        
        elif choice == "4":
            fnode = ""
            for node in nodes:
                resp = input("Insert in node: " + node + " ? (y/N)")
                if resp.lower() == "y":
                    fnode = node
                    break

            if fnode == "":
                continue

            owner = input("     Owner:")
            amount = float(input("     Amount:"))

            response = requests.post(fnode+"/deposit", data={
                "owner":owner,
                "amount":str(amount),
                "consenso":"1"
            })

            print("     Result: ", response.status_code)

        elif choice == "5":
            print("Exiting the program. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please choose a valid option.")

if __name__ == "__main__":
    main_menu()