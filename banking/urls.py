from django.urls import re_path

from banking import views


urlpatterns = [
    re_path(r"^$", views.ApiRootView.as_view(), name="api-root"),
    re_path(r"^auth/signup/?$", views.SignupView.as_view(), name="signup"),
    re_path(r"^auth/login/?$", views.LoginView.as_view(), name="login"),
    re_path(r"^auth/logout/?$", views.LogoutView.as_view(), name="logout"),
    re_path(r"^auth/me/?$", views.MeView.as_view(), name="me"),
    re_path(r"^customers/?$", views.CustomerListView.as_view(), name="customer-list"),
    re_path(
        r"^customers/(?P<pk>\d+)/?$",
        views.CustomerDetailView.as_view(),
        name="customer-detail",
    ),
    re_path(
        r"^customers/(?P<pk>\d+)/accounts/?$",
        views.CustomerAccountsView.as_view(),
        name="customer-accounts",
    ),
    re_path(r"^accounts/?$", views.AccountListView.as_view(), name="account-list"),
    re_path(
        r"^accounts/(?P<pk>\d+)/?$",
        views.AccountDetailView.as_view(),
        name="account-detail",
    ),
    re_path(
        r"^accounts/(?P<pk>\d+)/deposit/?$",
        views.DepositView.as_view(),
        name="account-deposit",
    ),
    re_path(
        r"^accounts/(?P<pk>\d+)/withdraw/?$",
        views.WithdrawView.as_view(),
        name="account-withdraw",
    ),
    re_path(
        r"^accounts/(?P<pk>\d+)/transactions/?$",
        views.AccountTransactionsView.as_view(),
        name="account-transactions",
    ),
]
