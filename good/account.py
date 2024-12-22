class Account:
    def __init__(self, initial_balance, owner):
        self.owner = owner
        self.balance = initial_balance

    def deposit(self, amount):
        self.balance += amount

    def withdraw(self, amount):
        if amount <= self.balance:
            self.balance -= amount
            return True
        return False
    
    def to_dict(self):
        return {
            "owner": self.owner,
            "balance": self.balance
        }

    def __str__(self):
        return f"Account from {self.owner} has Balance: {self.balance} Euros"
