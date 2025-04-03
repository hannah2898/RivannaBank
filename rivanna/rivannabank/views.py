from django.shortcuts import render,HttpResponse,redirect
from .models import Customer, Login, Account
from django.contrib import messages
from django.utils import timezone
from django.db import connection

import hashlib
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime

# Create your views here.
def home(request):
    return render(request,"home.html")

def createAccount(request):
    if request.method == 'POST':
        fullname = request.POST['fullname']
        phone = request.POST['phone']
        email = request.POST['email']
        address = f"{request.POST['streetAddress']}, {request.POST['address2']}, {request.POST['city']}, {request.POST['province']} - {request.POST['zipcode']}"
        username = request.POST['username']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('/Create-Account')

        with connection.cursor() as cursor:
            # Check if email already exists in Customer
            cursor.execute("SELECT 1 FROM rivannabank_customer WHERE email = %s", [email])
            if cursor.fetchone():
                messages.error(request, "Email is already registered.")
                return redirect('/Create-Account')

            # Check if username already exists in Login
            cursor.execute("SELECT 1 FROM rivannabank_login WHERE username = %s", [username])
            if cursor.fetchone():
                messages.error(request, "Username is already taken.")
                return redirect('/Create-Account')

            # Insert into Customer
            cursor.execute("""
                INSERT INTO rivannabank_customer (full_name, phone, email, address, date_created)
                VALUES (%s, %s, %s, %s, NOW())
            """, [fullname, phone, email, address])
            customer_id = cursor.lastrowid

            # Hash password
            password_hash = make_password(password)

            # Insert into Login
            cursor.execute("""
                INSERT INTO rivannabank_login (username, password_hash, customer_id)
                VALUES (%s, %s, %s)
            """, [username, password_hash, customer_id])

            # Insert into Account
            cursor.execute("""
                INSERT INTO rivannabank_account (account_type, balance, date_opened, customer_id)
                VALUES (%s, %s, NOW(), %s)
            """, ['Savings', 0.00, customer_id])

        messages.success(request, "Account created successfully!")
        return redirect('/')

    return render(request, 'create_account.html')


def login(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        password = request.POST['password'].strip()

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, password_hash 
                FROM rivannabank_login 
                WHERE username = %s
            """, [username])

            row = cursor.fetchone()

            if row is None:
                messages.error(request, "Username not found.")
                return redirect('/Login')

            user_id, stored_password_hash = row

            if check_password(password, stored_password_hash):
                cursor.execute("""
                    UPDATE rivannabank_login 
                    SET last_login = %s 
                    WHERE id = %s
                """, [datetime.now(), user_id])

                request.session['user_id'] = user_id
                messages.success(request, "Login successful.")
                return redirect('/')
            else:
                messages.error(request, "Incorrect password.")
                return redirect('/Login')

    return render(request, 'login.html')
 

def sendMoney(request):
    return render(request,"sendMoney.html")
def transactionHistory(request):
    return render(request,"transactionHistory.html")
def checkBalance(request):
    return render(request,"checkBalance.html")
def deposit(request):
    return render(request,"deposit.html")