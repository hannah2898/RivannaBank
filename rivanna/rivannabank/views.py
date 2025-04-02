from django.shortcuts import render,HttpResponse,redirect
from .models import Customer, Login, Account
from django.contrib import messages
from django.utils import timezone
import hashlib
# Create your views here.
def home(request):
    return render(request,"home.html")

def createAccount(request):
    if request.method == 'POST':
        full_name = request.POST['fullname']
        phone = request.POST['phone']
        email = request.POST['email']
        street = request.POST['streetAddress']
        address2 = request.POST['address2']
        city = request.POST['city']
        province = request.POST['province']
        zipcode = request.POST['zipcode']
        username = request.POST['username']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # Combine address
        full_address = f"{street}, {address2}, {city}, {province} - {zipcode}"

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('/Create-Account/')

        # Check if username or email already exists
        if Login.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect('/Create-Account/')
        if Customer.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('/Create-Account/')

        # Create Customer
        customer = Customer.objects.create(
            full_name=full_name,
            phone=phone,
            email=email,
            address=full_address,
            date_created=timezone.now()
        )

        # Hash password (basic, for example only)
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Create Login
        Login.objects.create(
            username=username,
            password_hash=password_hash,
            last_login=None,
            customer=customer
        )

        # Create Account (e.g., default savings)
        Account.objects.create(
            account_type="Savings",
            balance=0.00,
            customer=customer
        )

        messages.success(request, "Account created successfully!")
        return redirect('/')  # redirect to login or homepage

    return render(request, 'create_account.html')


def login(request):
    return render(request,"login.html")
def sendMoney(request):
    return render(request,"sendMoney.html")
def transactionHistory(request):
    return render(request,"transactionHistory.html")
def checkBalance(request):
    return render(request,"checkBalance.html")
def deposit(request):
    return render(request,"deposit.html")