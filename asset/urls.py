from django.urls import path
from .views import StockDataView, DividendData,DividendSummary, DividendYield, IncomeStatement, BalanceSheet, CashFlow ,PriceHistory, AssetSummary, AssetNews, LogoImage

urlpatterns = [
    path('asset/', StockDataView.as_view()),
    path('asset/price-history/', PriceHistory.as_view()),
    path('asset/summary/', AssetSummary.as_view()),
    path('asset/news/', AssetNews.as_view()),
    path('asset/logo/', LogoImage.as_view()),

    path('asset/dividend/', DividendData.as_view()),
    path('asset/dividend/summary/', DividendSummary.as_view()),
    path('asset/dividend/yield/', DividendYield.as_view()),

    path('asset/financials/income-statement/', IncomeStatement.as_view()),
    path('asset/financials/balance-sheet/', BalanceSheet.as_view()),
    path('asset/financials/cash-flow/', CashFlow.as_view()),
    
]