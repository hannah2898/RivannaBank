from django.db import models, transaction   
from decimal import Decimal
# Create your models here.
#Customer model represents a bank customer
class Customer(models.Model):
    full_name = models.CharField(max_length=45)
    phone = models.CharField(max_length=45, unique=True)
    email = models.EmailField(max_length=45, unique=True)
    address = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
# Account model represents a bank account
class Account(models.Model):
    account_type = models.CharField(max_length=50, null=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    date_opened = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)  # Assumes you have a Customer model

    def __str__(self):
        return f"Account {self.id} - {self.account_type}"
    
#Login model represents a customer's login stats
class Login(models.Model):
    username = models.CharField(max_length=45, unique=True)
    password_hash = models.CharField(max_length=255)
    last_login = models.DateTimeField(null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    def __str__(self):
        return self.username
# Transaction model represents deposits and withdrawals
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('Deposit', 'Deposit'),
        ('Withdrawal', 'Withdrawal'),
        ('E-Transfer', 'E-Transfer'), 
    )
    
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)  # Transaction type
    amount = models.DecimalField(max_digits=15, decimal_places=2)  # Transaction amount
    date = models.DateTimeField(auto_now_add=True)  # Auto timestamp when created
    status = models.CharField(max_length=50, default='Initiated')  # Transaction status
    account = models.ForeignKey('Account', on_delete=models.CASCADE)  # Links to an account
    balance_after_transaction = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # 👈 NEW

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.status}"

    def save(self, *args, **kwargs):
        # Use atomic transaction to ensure balance is updated safely
        with transaction.atomic():
            if self.transaction_type == 'Deposit':
                self.account.balance += self.amount
            elif self.transaction_type == 'Withdrawal':
                if self.account.balance >= self.amount:
                    self.account.balance -= self.amount
                else:
                    raise ValueError("Insufficient balance for sending money")

            # Save the updated account balance
            self.account.save()
            self.balance_after_transaction = self.account.balance
            # Save the transaction itself
            super(Transaction, self).save(*args, **kwargs)


# FundTransfer model represents money transfers between accounts
class FundTransfer(models.Model):
    amount = models.DecimalField(max_digits=15, decimal_places=2)  # Transfer amount
    date = models.DateTimeField(auto_now_add=True)  # Auto timestamp when created
    status = models.CharField(max_length=45, default='Initiated')  # Transfer status
    sender_account = models.ForeignKey('Account', related_name='sent_transfers', on_delete=models.CASCADE)  # Sender's account
    receiver_account = models.ForeignKey('Account', related_name='received_transfers', on_delete=models.CASCADE)  # Receiver's account

    def __str__(self):
        return f"{self.sender_account.customer.full_name} -> {self.receiver_account.customer.full_name}: {self.amount}"

    def save(self, *args, **kwargs):
        # Use atomic transaction to ensure transfer is handled safely
        with transaction.atomic():
            if not isinstance(self.amount, Decimal):
                self.amount = Decimal(str(self.amount))

        if self.sender_account.balance >= self.amount:
            self.sender_account.balance -= self.amount
            self.receiver_account.balance += self.amount

            Transaction.objects.create(
                transaction_type='E-Transfer',
                amount=-self.amount,
                account=self.sender_account,
                status='Completed',
                balance_after_transaction=self.sender_account.balance
            )
            Transaction.objects.create(
                transaction_type='E-Transfer',
                amount=self.amount,
                account=self.receiver_account,
                status='Completed',
                balance_after_transaction=self.receiver_account.balance
            )

            self.sender_account.save()
            self.receiver_account.save()

            self.status = 'Completed'
            super(FundTransfer, self).save(*args, **kwargs)
        else:
            raise ValueError("Insufficient balance for fund transfer")