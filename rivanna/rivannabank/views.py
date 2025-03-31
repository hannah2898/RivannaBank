from django.shortcuts import render,HttpResponse

# Create your views here.
def home(request):
    return render(request,"home.html")

def createAccount(request):
    return render(request,"createAccount.html")

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