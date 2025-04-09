from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db import connection, transaction
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime
import logging

from .models import Login, Customer, Account, Transaction

logger = logging.getLogger(__name__)

def hash_password(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def home(request):
    return render(request, "home.html")

def is_logged_in(request):
    return request.session.get('customer_id') is not None

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
            cursor.execute("SELECT 1 FROM rivannabank_customer WHERE email = %s", [email])
            if cursor.fetchone():
                messages.error(request, "Email is already registered.")
                return redirect('/Create-Account')

            cursor.execute("SELECT 1 FROM rivannabank_login WHERE username = %s", [username])
            if cursor.fetchone():
                messages.error(request, "Username is already taken.")
                return redirect('/Create-Account')

            cursor.execute("""
                INSERT INTO rivannabank_customer (full_name, phone, email, address, date_created)
                VALUES (%s, %s, %s, %s, NOW())
            """, [fullname, phone, email, address])
            customer_id = cursor.lastrowid

            password_hash = make_password(password)

            cursor.execute("""
                INSERT INTO rivannabank_login (username, password_hash, customer_id)
                VALUES (%s, %s, %s)
            """, [username, password_hash, customer_id])

            cursor.execute("""
                INSERT INTO rivannabank_account (account_type, balance, date_opened, customer_id)
                VALUES (%s, %s, NOW(), %s), (%s, %s, NOW(), %s)
            """, ['Savings', 0.00, customer_id, 'Chequing', 0.00, customer_id])

        messages.success(request, "Account created successfully!")
        return redirect('message.html')

    return render(request, 'create_account.html')

def login(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        password = request.POST['password'].strip()

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, password_hash, customer_id
                FROM rivannabank_login 
                WHERE username = %s
            """, [username])
            row = cursor.fetchone()

            if row is None:
                messages.error(request, "Username not found.")
                return redirect('/Login')

            user_id, stored_password_hash, customer_id = row

            if check_password(password, stored_password_hash):
                cursor.execute("""
                    UPDATE rivannabank_login 
                    SET last_login = %s 
                    WHERE id = %s
                """, [datetime.now(), user_id])

                request.session['user_id'] = user_id
                request.session['customer_id'] = customer_id
                messages.success(request, "Login successful.")
                return redirect('/')
            else:
                messages.error(request, "Incorrect password.")
                return redirect('/Login')

    return render(request, 'login.html')

def logout(request):
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('/Login')

def deposit(request):
    if not is_logged_in(request):
        messages.error(request, "You must be logged in to access this page.")
        return render(request, 'message.html')

    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount'))
        except ValueError:
            messages.error(request, "Invalid amount format.")
            return redirect('/deposit')

        password = request.POST.get('password')
        account_type = request.POST.get('account_type')

        customer_id = request.session.get('customer_id')
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, password_hash 
                    FROM rivannabank_login 
                    WHERE customer_id = %s
                """, [customer_id])
                login_row = cursor.fetchone()

                if login_row is None:
                    messages.error(request, "Login record not found.")
                    return redirect('/deposit')

                login_id, password_hash = login_row

                if not check_password(password, password_hash):
                    messages.error(request, "Incorrect password.")
                    return redirect('/deposit')

                cursor.execute("""
                    SELECT id, balance 
                    FROM rivannabank_account 
                    WHERE customer_id = %s AND account_type = %s
                """, [customer_id, account_type])
                account_row = cursor.fetchone()

                if not account_row:
                    messages.error(request, f"No {account_type} account found.")
                    return redirect('/deposit')

                account_id, current_balance = account_row
                new_balance = float(current_balance) + amount

                logger.info(f"Current balance: {current_balance}")
                logger.info(f"New balance: {new_balance}")
                logger.info(f"Account ID: {account_id}")
                logger.info(f"Amount: {amount}")

                with transaction.atomic():
                    cursor.execute("""
                        UPDATE rivannabank_account 
                        SET balance = %s 
                        WHERE id = %s
                    """, [new_balance, account_id])

                    cursor.execute("""
                        INSERT INTO rivannabank_transaction 
                        (transaction_type, amount, date, status, account_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, ['Deposit', amount, timezone.now(), 'Completed', account_id])

            messages.success(request, f"Deposit of ₹{amount} to your {account_type} account successful!")
            return redirect('/')

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Exception during deposit: {e}")
            messages.error(request, f"Error: {str(e)}")
            return redirect('/deposit')

    return render(request, 'deposit.html')

def sendMoney(request):
    if not is_logged_in(request):
        messages.error(request, "You must be logged in to access this page.")
        return render(request, 'message.html')
    return render(request, "sendMoney.html")

def transactionHistory(request):
    if not is_logged_in(request):
        messages.error(request, "You must be logged in to access this page.")
        return render(request, 'message.html')
    return render(request, "transactionHistory.html")

def checkBalance(request):
    if not is_logged_in(request):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Not logged in'}, status=403)
        messages.error(request, "You must be logged in to check your balance.")
        return render(request, 'message.html')

    if request.method == 'POST':
        password = request.POST.get('password')
        account_type = request.POST.get('account_type')
        customer_id = request.session.get('customer_id')

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT password_hash 
                    FROM rivannabank_login 
                    WHERE customer_id = %s
                """, [customer_id])
                row = cursor.fetchone()

                if row is None:
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'error': 'Login not found.'}, status=404)
                    messages.error(request, "Login not found.")
                    return redirect('/Check-Balance')

                stored_password_hash = row[0]

                if not check_password(password, stored_password_hash):
                    error_msg = "Incorrect password."
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'error': error_msg}, status=403)
                    return redirect('/Check-Balance', {'error': error_msg})

                cursor.execute("""
                    SELECT balance 
                    FROM rivannabank_account 
                    WHERE customer_id = %s AND account_type = %s
                """, [customer_id, account_type])
                row = cursor.fetchone()

                if row:
                    balance = float(row[0])
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'balance': balance})
                    return render(request, 'checkBalance.html', {'balance': balance})
                else:
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'error': f"{account_type.capitalize()} account not found."}, status=404)
                    messages.error(request, f"{account_type.capitalize()} account not found.")
        except Exception as e:
            logger.error(f"Exception in checkBalance: {e}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Internal server error.'}, status=500)
            messages.error(request, "Something went wrong while fetching your balance.")

    return render(request, 'checkBalance.html')