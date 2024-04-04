from django.urls import path
from .views import (
    CreatePortfolio,
    GetAllPortfolios,
    UpdatePortfolio,
    DeletePortfolio,
    CreateTransaction,
    GetAssets,
    GetTransactions,
    DeleteTransaction,
    GetPortfolioValue,
    GetDividendsReceived,
    GetPortfolioValueOverTime,
    GetPortfolioNews,
    GetPortfolioMetrics,
    GetSPMetrics
)

urlpatterns = [
    path('create/', CreatePortfolio.as_view()),
    path('get-all/<int:user_id>/', GetAllPortfolios.as_view()),
    path('update/<int:portfolio_id>/', UpdatePortfolio.as_view()),
    path('delete/<int:portfolio_id>/', DeletePortfolio.as_view()),

    path('create-transaction/', CreateTransaction.as_view()),
    path('<int:portfolio_id>/assets/', GetAssets.as_view()),
    path('<int:portfolio_id>/transactions/', GetTransactions.as_view()),
    path('transaction/<int:transaction_id>/delete/', DeleteTransaction.as_view()),
    path('portfolio-value/<int:portfolio_id>/', GetPortfolioValue.as_view()),
    path('<int:portfolio_id>/dividends/', GetDividendsReceived.as_view()),
    path('<int:portfolio_id>/portfoliovalue/', GetPortfolioValueOverTime.as_view()),
    path('<int:portfolio_id>/portfolionews/', GetPortfolioNews.as_view()),
    path('<int:portfolio_id>/portfoliometrics/', GetPortfolioMetrics.as_view()),
    path('spmetrics/', GetSPMetrics.as_view()),
]