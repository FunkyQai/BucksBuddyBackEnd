from decimal import Decimal
import json
from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseServerError
import pytz
import os
import requests
from .models import Portfolio, Asset, Transaction
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from .serializers import TransactionSerializer
from .serializers import AssetSerializer
import yfinance as yf
import pandas as pd
import numpy as np
from django.utils.dateparse import parse_datetime
from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import USFederalHolidayCalendar
from datetime import datetime, timedelta
from django.test.client import RequestFactory

User = get_user_model()


def create_portfolio(user_id, name, remarks=''):
    user = User.objects.get(id=user_id)
    portfolio = Portfolio.objects.create(user=user, name=name, remarks=remarks)
    return portfolio

@method_decorator(csrf_exempt, name='dispatch')
class CreatePortfolio(View):
    def post(self, request):
        data = json.loads(request.body)
        portfolio = create_portfolio(data['user_id'], data['name'], data.get('remarks', ''))
        return JsonResponse({
            'id': portfolio.id, 
            'user_id': portfolio.user.id, 
            'name': portfolio.name, 
            'remarks': portfolio.remarks,
        }, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class GetAllPortfolios(View):
    def get(self, request, user_id):
        portfolios = Portfolio.objects.filter(user_id=user_id)
        portfolios_list = [{'id': p.id, 'name': p.name, 'remarks': p.remarks, 'value': p.total_value()} for p in portfolios]
        return JsonResponse(portfolios_list, safe=False)
    
@method_decorator(csrf_exempt, name='dispatch')
class UpdatePortfolio(View):
    def put(self, request, portfolio_id):
        data = json.loads(request.body)
        portfolio = Portfolio.objects.get(id=portfolio_id)
        portfolio.name = data.get('name', portfolio.name)
        portfolio.remarks = data.get('remarks', portfolio.remarks)
        portfolio.save()
        return JsonResponse({
            'id': portfolio.id,
            'user_id': portfolio.user.id,
            'name': portfolio.name,
            'remarks': portfolio.remarks,
        }, status=200)
    
@method_decorator(csrf_exempt, name='dispatch')
class DeletePortfolio(View):
    def delete(self, request, portfolio_id):
        portfolio = Portfolio.objects.get(id=portfolio_id)
        portfolio.delete()
        return JsonResponse({'message': 'Portfolio deleted successfully'}, status=200)
    
@method_decorator(csrf_exempt, name='dispatch')
class AssetView(View):
    def post(self, request):
        data = json.loads(request.body)
        portfolio = Portfolio.objects.get(id=data['portfolio_id'])
        asset = Asset.objects.create(
            portfolio=portfolio, 
            name=data['name'], 
            ticker=data['ticker'], 
            type=data['type'], 
            sector=data['sector'], 
            units=data['units'], 
            averagePrice=data['averagePrice']
        )
        return JsonResponse({
            'id': asset.id, 
            'name': asset.name, 
            'ticker': asset.ticker, 
            'type': asset.type, 
            'sector': asset.sector, 
            'units': asset.units, 
            'averagePrice': asset.averagePrice, 
            'value': asset.value(), 
            'portfolio': portfolio.name 
        }, status=201)

def create_transaction(portfolio_id, transaction_type, asset_name, asset_ticker, asset_type, asset_sector, units, price, fee=0, transaction_date=None):
    portfolio = Portfolio.objects.get(id=portfolio_id)
    transaction_date = parse_datetime(transaction_date) if transaction_date else timezone.now()

    # Get or create the Asset instance
    asset, created = Asset.objects.get_or_create(
        portfolio=portfolio,
        name=asset_name, 
        ticker=asset_ticker,
        type=asset_type,
        sector=asset_sector,
    )

    transaction = Transaction.objects.create(
        portfolio=portfolio, 
        transaction_type=transaction_type, 
        asset=asset,  # Use the Asset instance
        asset_name=asset_name,
        ticker=asset_ticker,
        units=float(units), 
        price=float(price), 
        fee=float(fee), 
        transaction_date=transaction_date
    )
    return transaction

@method_decorator(csrf_exempt, name='dispatch')        
class CreateTransaction(View):
    def post(self, request):
        data = json.loads(request.body)
        transaction = create_transaction(
            data['pid'], 
            data['transaction_type'], 
            data['asset_name'], 
            data['asset_ticker'], 
            data['asset_type'], 
            data['asset_sector'], 
            data['units'], 
            data['price'], 
            data.get('fee', 0), 
            data.get('transaction_date')
        )
        return JsonResponse({
            'id': transaction.id, 
            'portfolio_id': transaction.portfolio.id, 
            'ticker': transaction.ticker,
            'transaction_type': transaction.transaction_type, 
            'asset': transaction.asset.id,  # Return the ID of the Asset instance
            'units': transaction.units, 
            'price': transaction.price, 
            'fee': transaction.fee, 
            'transaction_date': transaction.transaction_date,
        }, status=201)
    
@method_decorator(csrf_exempt, name='dispatch')
class GetAssets(View):
    def get(self, request, portfolio_id):
        # Fetch the portfolio
        portfolio = Portfolio.objects.get(id=portfolio_id)

        # Fetch all assets related to the portfolio
        assets = Asset.objects.filter(portfolio=portfolio)

        # Serialize the assets into a list of dictionaries
        assets_data = list(assets.values())

        # Get the current price for each asset and add it to the asset's data
        for asset_data in assets_data:
            ticker = asset_data['ticker']
            units = float(asset_data['units'])
            averagePrice = float(asset_data['averagePrice'])
            info = yf.Ticker(ticker).info
            currentPrice = round(info.get('regularMarketOpen'), 2)
            asset_data['currentPrice'] = currentPrice

            # Compute the value of the asset
            asset_data['currentValue'] = round(currentPrice * units, 2)

            # Compute the profit
            profit = round(((currentPrice - averagePrice) * units), 2)
            asset_data['profit'] = profit

            # Compute the percentage change
            if averagePrice != 0:
                percentageChange = round(((currentPrice - averagePrice) / averagePrice) * 100, 2)
            else:
                percentageChange = 0
            asset_data['percentageChange'] = percentageChange

        # Return the data as JSON
        return JsonResponse(assets_data, safe=False)
    
@method_decorator(csrf_exempt, name='dispatch')
class GetTransactions(View):
    def get(self, request, portfolio_id):
        # Fetch the portfolio
        portfolio = Portfolio.objects.get(id=portfolio_id)

        # Fetch all transactions related to the portfolio
        transactions = Transaction.objects.filter(portfolio=portfolio)

        # Serialize the transactions into a list of dictionaries
        serializer = TransactionSerializer(transactions, many=True)
        transactions_data = serializer.data

        # Return the data as JSON
        return JsonResponse(transactions_data, safe=False)
    
@method_decorator(csrf_exempt, name='dispatch')
class DeleteTransaction(View):
    def delete(self, request, transaction_id):
        try:
            transaction = Transaction.objects.get(id=transaction_id)
            transaction.delete()
            return JsonResponse({'message': 'Transaction deleted successfully'}, status=200)
        except Transaction.DoesNotExist:
            return JsonResponse({'error': 'Transaction not found'}, status=404)
        
@method_decorator(csrf_exempt, name='dispatch')
class GetPortfolioValue(View):
    def get(self, request, portfolio_id):
        # Fetch the portfolio
        portfolio = get_object_or_404(Portfolio, id=portfolio_id)

        # Fetch all the assets in the portfolio
        assets = Asset.objects.filter(portfolio=portfolio)

        # Serialize the assets into a list of tickers
        serializer = AssetSerializer(assets, many=True)

        # Use the yfinance API to get asset information for each ticker
        portfolio_value = 0
        annual_dividends = 0
        for asset in serializer.data:
            ticker = asset['ticker']
            units = float(asset['units'])  # Convert units to float
            info = yf.Ticker(ticker).info
            regular_market_open = info.get('regularMarketOpen')
            trailing_annual_dividend_rate = info.get('trailingAnnualDividendRate')
            if regular_market_open is not None:
                value = regular_market_open * units
                portfolio_value += value
            if trailing_annual_dividend_rate is not None:
                annual_dividends += trailing_annual_dividend_rate * units

        # Calculate the amount invested
        amount_invested = float(portfolio.total_value())  # Convert amount_invested to float

        # Calculate the percentage change
        percentage_change = ((portfolio_value - amount_invested) / amount_invested) * 100 if amount_invested != 0 else 0

        realisedPL = float(portfolio.total_RealisedPL())
        total_fees = float(portfolio.total_fees())

        # Calculate the profit
        profit = portfolio_value - amount_invested + realisedPL - total_fees

        # Calculate the profit percentage change
        profit_percentage_change = (profit / (amount_invested + total_fees)) * 100 if (amount_invested + total_fees) != 0 else 0

        # Calculate the monthly dividends
        monthly_dividends = annual_dividends / 12

        # Return the portfolio value, amount invested, and percentage change as JSON
        return JsonResponse({
            'portfolio value': round(portfolio_value, 2),
            'Amount invested': round(amount_invested, 2),
            'Percentage change': round(percentage_change, 2),
            'Realised P/L': round(realisedPL, 2),
            'Total fees': round(total_fees, 2),
            'Profit': round(profit, 2),
            'Profit percentage change': round(profit_percentage_change, 2),
            'Annual dividends': round(annual_dividends, 2),
            'Monthly dividends': round(monthly_dividends, 2)
        })

@method_decorator(csrf_exempt, name='dispatch')
class GetDividendsReceived(View):
    def get(self, request, portfolio_id):
        # Fetch the portfolio
        portfolio = Portfolio.objects.get(id=portfolio_id)

        # Fetch all transactions related to this portfolio
        transactions = Transaction.objects.filter(portfolio=portfolio)

        # Initialize a dictionary to store the total dividends for each asset
        dividends = {}

        # Iterate through the transactions
        for transaction in transactions:
            # Fetch the dividends data for the asset
            stock = yf.Ticker(transaction.ticker)
            data = stock.dividends

            # Convert the transaction date and the current date to timezone-aware datetime objects
            transaction_date = transaction.transaction_date.replace(tzinfo=pytz.UTC)
            current_date = timezone.now().astimezone(pytz.UTC)

            # Check if data is a pandas Series
            if isinstance(data, pd.Series):
                # Convert the index of the dividends data to UTC
                data.index = data.index.tz_convert('UTC')

                # Filter the dividends data to only include dividends from the transaction date to the current date
                data = data[(data.index >= transaction_date) & (data.index <= current_date)]

                # Calculate the total dividends during this period
                total_dividends = Decimal(sum(data.values)) * transaction.units
            else:
                total_dividends = 0

            # If the transaction is a "buy" transaction, add the total dividends to the total dividends for the asset
            if transaction.transaction_type == 'buy':
                dividends[transaction.ticker] = dividends.get(transaction.ticker, 0) + total_dividends

            # If the transaction is a "sell" transaction, subtract the total dividends from the total dividends for the asset
            elif transaction.transaction_type == 'sell':
                dividends[transaction.ticker] = dividends.get(transaction.ticker, 0) - total_dividends

        # Filter out assets with dividends <= 0 and format the dividends to 2 decimal places
        dividends = {ticker.upper(): '{:.2f}'.format(dividend) for ticker, dividend in dividends.items() if dividend > 0}

        # Return the total dividends for each asset
        return JsonResponse(dividends)
    
@method_decorator(csrf_exempt, name='dispatch')
class GetPortfolioValueOverTime(View):
    def get(self, request, portfolio_id):
        # Get the current date
        current_date = datetime.now()

        # Subtract one day
        end_date = current_date - timedelta(days=1)

        # Get all transactions for the portfolio excluding those made today, sorted by date
        transactions = Transaction.objects.filter(portfolio_id=portfolio_id).order_by('transaction_date')
    
        # If there are no transactions, return an empty JSON response
        if not transactions.exists():
            return JsonResponse({})

        # Initialize a list to store the dataframes
        dfs = []

        # Define a custom business day Calendar
        custom_business_day = CustomBusinessDay(calendar=USFederalHolidayCalendar())

        # For each transaction
        for transaction in transactions:
            # Get the date of the transaction without the time segment
            start_date = transaction.transaction_date.astimezone(pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0)

            # Fetch all the historical price data for the asset from the transaction date to the current date
            data = yf.Ticker(transaction.ticker)
            historical_data = data.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))[['Open']]

            # Remove weekends and holidays
            historical_data = historical_data[historical_data.index.to_series().map(custom_business_day.is_on_offset)]
            
            # Check if 'Open' column exists in the DataFrame
            if 'Open' in historical_data.columns:
                # Multiply the opening price by the number of units in the transaction
                historical_data['Open'] *= float(transaction.units)

                # If the transaction is a sell, multiply the opening price by -1
                if transaction.transaction_type == 'sell':
                    historical_data['Open'] *= -1

                # Add the dataframe to the list
                dfs.append(historical_data)
            else:
                # Handle the case when 'Open' column does not exist
                # You might want to log an error message or throw an exception
                print(f"No 'Open' column in historical data for transaction {transaction.id}")

        # Concatenate all the dataframes
        portfolio_value_over_time = pd.concat(dfs)

        # Convert the index to a DatetimeIndex in UTC
        portfolio_value_over_time.index = pd.to_datetime(portfolio_value_over_time.index, utc=True)

        # Group by date and sum up the opening prices
        portfolio_value_over_time = portfolio_value_over_time.groupby(portfolio_value_over_time.index.date).sum()

        # Convert the dataframe to a dictionary and convert the Timestamp keys to strings
        portfolio_value_over_time = portfolio_value_over_time['Open'].to_dict()
        portfolio_value_over_time = {str(k): v for k, v in portfolio_value_over_time.items()}

        # Return the portfolio value over time as a JSON response
        return JsonResponse(portfolio_value_over_time)
    
@method_decorator(csrf_exempt, name='dispatch')
class GetPortfolioNews(View):
    def get(self, request, portfolio_id):
        # Fetch the portfolio
        portfolio = Portfolio.objects.get(id=portfolio_id)

        # Fetch all assets related to the portfolio
        assets = Asset.objects.filter(portfolio=portfolio)

        # Serialize the assets into a list of tickers
        serializer = AssetSerializer(assets, many=True)
        tickers = [asset['ticker'] for asset in serializer.data]

        # Convert the list of tickers into a comma-separated string
        tickers_string = ','.join(tickers)

        api_key = os.getenv('NEWS_API_KEY')
        if api_key is None:
            return HttpResponseServerError("NEWS_API_KEY is not set.")
        
        response = requests.get('https://api.marketaux.com/v1/news/all', params={'symbols': tickers_string, 'language': 'en', "api_token": api_key, "filter_entities":"true"})
        if response.status_code == 200:
            data = response.json()
            response = JsonResponse(data)  # Create the JsonResponse
            response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
            return response
        else:
            return HttpResponseBadRequest('API request failed.')

@method_decorator(csrf_exempt, name='dispatch')
class GetPortfolioMetrics(View):
    def get(self, request, portfolio_id):
        # Fetch the portfolio
        portfolio = Portfolio.objects.get(id=portfolio_id)

        # Fetch all assets related to the portfolio
        assets = Asset.objects.filter(portfolio=portfolio)

        # Serialize the assets into a list of tickers
        serializer = AssetSerializer(assets, many=True)
        tickers = [asset['ticker'] for asset in serializer.data]

        # Use the yfinance API to get asset information for each ticker
        stock_data = yf.download(' '.join(tickers), period="5y")[['Adj Close']]
        stock_data = stock_data.dropna()

        # Calculate the percentage change for each asset and drop the NaN values
        stock_returns = stock_data.pct_change().dropna()

        # Only remove the first level of the MultiIndex from the columns if there is more than one level
        if stock_returns.columns.nlevels > 1:
            stock_returns.columns = stock_returns.columns.droplevel(0)

        # Calculate the asset allocation of the portfolio
        portfolio_value = 0
        values = []
        allocations = []
        for asset in serializer.data:
            ticker = asset['ticker']
            units = float(asset['units'])  # Convert units to float
            info = yf.Ticker(ticker).info
            regular_market_open = info.get('regularMarketOpen')
            if regular_market_open is not None:
                value = regular_market_open * units
                portfolio_value += value
                values.append(value)
        
        for value in values:
            allocations.append(round(value/portfolio_value, 3))

        # Create a dictionary mapping tickers to allocations
        allocations_dict = dict(zip(tickers, allocations))

        portfolio_returns = stock_returns.copy()

        # Calculate the returns for each asset
        for asset, allocation in zip(portfolio_returns.columns, allocations):
            portfolio_returns[asset] = portfolio_returns[asset] * allocation

        # Calculate portfolio return
        portfolio_returns['Portfolio_Return'] = portfolio_returns.sum(axis=1)

        # Assume a risk-free rate of 0
        risk_free_rate = 0

        # Calculate Sharpe Ratio and annualize it
        sharpe_ratio = (portfolio_returns['Portfolio_Return'].mean() - risk_free_rate) / portfolio_returns['Portfolio_Return'].std()
        sharpe_ratio = round(sharpe_ratio * np.sqrt(255), 2)

        # Calculate downside deviation
        downside_returns = portfolio_returns.loc[portfolio_returns['Portfolio_Return'] < risk_free_rate]
        downside_deviation = downside_returns.std()['Portfolio_Return']

        # Calculate Sortino Ratio and annualize it
        sortino_ratio = (portfolio_returns['Portfolio_Return'].mean() - risk_free_rate) / downside_deviation
        sortino_ratio = round(sortino_ratio * np.sqrt(255), 2)

        # Calculate expected annual return
        expected_annual_return = round(portfolio_returns['Portfolio_Return'].mean() * 255 * 100, 2)

        # Calculate annual volatility
        annual_volatility = round(portfolio_returns['Portfolio_Return'].std() * np.sqrt(255) * 100, 2)

        # Calculate correlation matrix
        corr_matrix = stock_returns.corr()

        return JsonResponse({
            "Portfolio Allocation": allocations_dict,
            "Sharpe Ratio": sharpe_ratio,
            "Sortino Ratio": sortino_ratio,
            "Expected Annual Return": expected_annual_return,
            "Annual Volatility": annual_volatility,
            "Correlation Matrix": corr_matrix.to_dict(),
        })

@method_decorator(csrf_exempt, name='dispatch')
class GetSPMetrics(View):
    def get(self, request):
        # Get the S&P 500 data
        sp500 = yf.download('^GSPC', period="5y")[['Adj Close']]
        sp500 = sp500.dropna()

        # Calculate the percentage change
        sp500_returns = sp500.pct_change().dropna()

        # Assume a risk-free rate of 0
        risk_free_rate = 0

        # Calculate Sharpe Ratio and annualize it
        sharpe_ratio = (sp500_returns.mean() - risk_free_rate) / sp500_returns.std()
        sharpe_ratio = round(sharpe_ratio.iloc[0] * np.sqrt(255), 2)

        # Calculate downside deviation
        downside_returns = sp500_returns.loc[sp500_returns['Adj Close'] < risk_free_rate]
        downside_deviation = downside_returns.std()['Adj Close']

        # Calculate Sortino Ratio and annualize it
        sortino_ratio = (sp500_returns.mean() - risk_free_rate) / downside_deviation
        sortino_ratio = round(sortino_ratio.iloc[0] * np.sqrt(255), 2)

        # Calculate the expected annual return
        expected_annual_return = round(sp500_returns.mean().iloc[0] * 255 * 100, 2)

        # Calculate the annual volatility
        annual_volatility = round(sp500_returns.std().iloc[0] * np.sqrt(255) * 100, 2)

        return JsonResponse({
            "Sharpe Ratio": sharpe_ratio,
            "Sortino Ratio": sortino_ratio,
            "Expected Annual Return": expected_annual_return,
            "Annual Volatility": annual_volatility
        })
    
def write_view_outputs_to_file(pid, filename):
    factory = RequestFactory()
    view_data = [(GetPortfolioValue, {'portfolio_id': pid}),
                 (GetPortfolioMetrics, {'portfolio_id': pid}),
                 (GetSPMetrics, {}),
                 (GetAssets, {'portfolio_id': pid}),
                 (GetDividendsReceived, {'portfolio_id': pid})]
    headers = {GetAssets: '**Assets in portfolio**', 
               GetPortfolioValue: '**Portfolio value, dividends and fees**', 
               GetDividendsReceived: '**Total dividends received from each stock**',
               GetPortfolioMetrics: '**Portfolio asset allocation and Metrics**',
               GetSPMetrics: '**S&P 500 metrics for comparison with portfolio metrics**'}
    with open(filename, 'w') as f:
        f.write('Portfolio Information:\n')  # Add header
        portfolio = Portfolio.objects.get(id=pid)
        f.write(f'User ID (uid): {portfolio.user.id}\n')
        f.write(f'Portfolio ID (pid): {portfolio.id}\n')
        f.write(f'Name: {portfolio.name}\n')
        f.write(f'Notes: {portfolio.remarks}\n')
        f.write(f'Date Created: {portfolio.dateCreated}\n')

        for view_class, kwargs in view_data:
            f.write(f'\n{headers[view_class]}\n')  # Add custom subheader
            request = factory.get('/')
            view_instance = view_class()
            response = view_instance.get(request, **kwargs)
            data = json.loads(response.content)
            # Exclude 'id' and 'portfolio_id' fields for GetAssets view
            if view_class == GetAssets:
                for item in data:
                    item.pop('id', None)
                    item.pop('portfolio_id', None)
            f.write(json.dumps(data, indent=4))
            f.write('\n')
