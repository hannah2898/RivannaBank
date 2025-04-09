from django.urls import path
from . import views

urlpatterns=[
    path("",views.home,name="home"),
    path("Create-Account",views.createAccount,name="create_account"),
    path("Login",views.login,name="login"),
    path("SendMoney",views.sendMoney,name="sendMoney"),
    path("Transaction-History",views.transactionHistory,name="transactionHistory"),
    path("Check-Balance",views.checkBalance,name="checkBalance"),
    path("Deposit",views.deposit,name="deposit"),
    path('login/', views.login, name='custom_login'),
    path('logout/', views.logout, name='custom_logout'),

]