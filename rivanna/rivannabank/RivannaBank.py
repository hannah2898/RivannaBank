from django.db import models, transaction

# Transaction model represents deposits and withdrawals
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('Deposit', 'Deposit'),
        ('Withdrawal', 'Withdrawal'),
    )
    
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)  # Transaction type
    amount = models.DecimalField(max_digits=15, decimal_places=2)  # Transaction amount
    date = models.DateTimeField(auto_now_add=True)  # Auto timestamp when created
    status = models.CharField(max_length=50, default='Initiated')  # Transaction status
    account = models.ForeignKey('Account', on_delete=models.CASCADE)  # Links to an account

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
                    raise ValueError("Insufficient balance for withdrawal")

            # Save the updated account balance
            self.account.save()

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
            if self.sender_account.balance >= self.amount:
                # Decrease sender balance
                self.sender_account.balance -= self.amount
                self.sender_account.save()

                # Increase receiver balance
                self.receiver_account.balance += self.amount
                self.receiver_account.save()

                # Mark transfer as completed
                self.status = 'Completed'

                # Save the transfer record
                super(FundTransfer, self).save(*args, **kwargs)
            else:
                raise ValueError("Insufficient balance for fund transfer")