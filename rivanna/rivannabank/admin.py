from django.contrib import admin
from .models import Customer, Account, Transaction, FundTransfer,Login

# Register your models here.
admin.site.register(Customer)
admin.site.register(Account)
admin.site.register(Transaction)
admin.site.register(FundTransfer)
admin.site.register(Login)