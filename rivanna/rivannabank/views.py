from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db import connection, transaction
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime
from decimal import Decimal
import logging

from .models import Login, Customer, Account, Transaction, FundTransfer

logger = logging.getLogger(__name__)

def hash_password(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def home(request):
    username = None
    if is_logged_in(request):
        try:
            customer_id = request.session.get('customer_id')
            customer = Customer.objects.get(id=customer_id)
            username = customer.full_name.split(" ")[0]  # just first name, if you want
        except Customer.DoesNotExist:
            pass  # fallback: no name shown

    return render(request, "home.html", {
        'logged_in': is_logged_in(request),
        'username': username
    })


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
        errors = {}
        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM rivannabank_customer WHERE email = %s", [email])
            if cursor.fetchone():
                errors['email'] = "Email is already registered."

            cursor.execute("SELECT 1 FROM rivannabank_login WHERE username = %s", [username])
            if cursor.fetchone():
                errors['username'] = "Username is already taken."
            if errors:
                return render(request, 'create_account.html', {
                    'errors': errors,
                    'form_data': request.POST
                })
            with connection.cursor() as cursor:
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
        return render(request, 'message.html')

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
                return render(request, 'message.html')

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
                return render(request, 'message.html')

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
            amount = Decimal(request.POST.get("amount"))
        except ValueError:
            messages.error(request, "Invalid amount format.")
            return redirect('/Deposit')

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
                    return redirect('/Deposit')

                login_id, password_hash = login_row

                if not check_password(password, password_hash):
                    messages.error(request, "Incorrect password.")
                    return redirect('/Deposit')

                cursor.execute("""
                    SELECT id, balance 
                    FROM rivannabank_account 
                    WHERE customer_id = %s AND account_type = %s
                """, [customer_id, account_type])
                account_row = cursor.fetchone()

                if not account_row:
                    messages.error(request, f"No {account_type} account found.")
                    return redirect('/Deposit')

                account_id, current_balance = account_row
                new_balance = Decimal(current_balance) + amount

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
            return render(request, 'message.html')

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Exception during deposit: {e}")
            messages.error(request, f"Error: {str(e)}")
            return redirect('/Deposit')

    return render(request, 'deposit.html')

def sendMoney(request):
    if not is_logged_in(request):
        messages.error(request, "You must be logged in to send money.")
        return render(request, 'message.html')
    if request.method == "POST":
        try:
            # Retrieve sender (assuming they are linked to a Login which links to Customer)
            customer_id = request.session.get('customer_id')
            sender = Customer.objects.get(id=customer_id)

            # Parse form data
            amount = Decimal(request.POST.get("amount"))
            account_type = request.POST.get("account_type")
            recipient_email = request.POST.get("email")

            # Sanity checks
            if amount <= Decimal('0.00'):
                messages.error(request, "Transfer amount must be greater than zero.")
                return render(request, 'message.html')

            # Get sender account (e.g., chequing/savings)
            try:
                sender_account = Account.objects.get(customer=sender, account_type=account_type)
            except Account.DoesNotExist:
                messages.error(request, "Your selected account type does not exist.")
                return render(request, 'message.html')
            # Check sufficient funds
            if sender_account.balance < amount:
                messages.error(request, "Insufficient funds in your account.")
                return render(request, 'message.html')

            # Get recipient customer and chequing account
            try:
                recipient_customer = Customer.objects.get(email=recipient_email)
                recipient_account = Account.objects.get(customer=recipient_customer, account_type="chequing")
            except Customer.DoesNotExist:
                messages.error(request, "Recipient email not registered.")
                return render(request, 'message.html')
            except Account.DoesNotExist:
                messages.error(request, "Recipient does not have a chequing account.")
                return render(request, 'message.html')

            # Transfer funds atomically
            with transaction.atomic():
                transfer = FundTransfer(
                    amount=amount,
                    sender_account=sender_account,
                    receiver_account=recipient_account
                )
                transfer.save()  # This will update balances inside the model
            messages.success(request, f"💸 ${amount:.2f} sent to {recipient_email} successfully.")
            return render(request, 'message.html')

        except Exception as e:
            messages.error(request, f"Something went wrong: {str(e)}")
            return render(request, 'message.html')

    return render(request, "sendMoney.html")


def transactionHistory(request):
    if not is_logged_in(request):
        messages.error(request, "You must be logged in to access this page.")
        return render(request, 'message.html')
    customer_id = request.session.get('customer_id')

    try:
        # Get all accounts of the logged-in customer
        accounts = Account.objects.filter(customer_id=customer_id)
        account_ids = accounts.values_list('id', flat=True)

        # Get all transactions related to these accounts, in descending order
        transactions = Transaction.objects.filter(account_id__in=account_ids).order_by('-date')

        return render(request, 'transactionHistory.html', {
            'transactions': transactions
        })

    except Exception as e:
        messages.error(request, f"Could not fetch transactions: {str(e)}")
        return render(request, 'message.html')


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