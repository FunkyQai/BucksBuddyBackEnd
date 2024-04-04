import pandas as pd
import yfinance as yf
import requests
from django.http import HttpResponseServerError, JsonResponse, HttpResponseBadRequest
from django.views import View
import os
import math
import numpy as np
from dotenv import load_dotenv

load_dotenv()

class StockDataView(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        stock = yf.Ticker(symbol)
        info = stock.info
        data = {
            'company_name': info.get('longName'),
            'price': f"{info.get('regularMarketOpen'):.2f}",
            'previous_close': f"{info.get('regularMarketPreviousClose'):.2f}",
            'ticker': info.get('symbol'),
            'country': info.get('country'),
            'sector': info.get('sector'),
            'website': info.get('website'),
            'about': info.get('longBusinessSummary'),
            'trailingPE': info.get('trailingPE'),
            'trailingEps': info.get('trailingEps'),
            'dividendYield': info.get('dividendYield'),
            'marketCap': info.get('marketCap'),
            'quoteType': info.get('quoteType'),
        }
        response = JsonResponse(data)  # Create the JsonResponse
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response
    
    
class DividendData(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        stock = yf.Ticker(symbol)
        data = stock.dividends  # Fetch stock dividends

        data.index = [date.isoformat() for date in data.index.to_pydatetime()]

        data_dict = {date: f"{value:.3f}" for date, value in data.items()}  # Convert the values to strings with 3 decimal places 

        response = JsonResponse(data_dict)  # Create the JsonResponse
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response
    
class DividendSummary(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        stock = yf.Ticker(symbol)
        info = stock.info
        data = {
            'dividendRate': info.get('dividendRate'),
            'dividendYield': info.get('dividendYield'),
            'payoutRatio': info.get('payoutRatio'),
            'trailingAnnualDividendRate': info.get('trailingAnnualDividendRate'),
            'trailingAnnualDividendYield': info.get('trailingAnnualDividendYield'),
            'lastDividendValue': info.get('lastDividendValue'),
        }
        response = JsonResponse(data)  # Create the JsonResponse
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response


class DividendYield(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        stock = yf.Ticker(symbol)

        data = stock.history(period='max')  # Fetch stock dividends
        data = data[data['Dividends'] > 0]
        data.reset_index(inplace=True)
        data = data[['Date', 'Close', 'Dividends']]
        data['Yield'] = (data['Dividends'] / data['Close'] * 100).round(2)  # Calculate dividend yield
        data = data.drop(['Close', 'Dividends'], axis=1) # Drop unnecessary columns

        data_dict = data.to_dict('records')  # Convert DataFrame to dictionary
        response = JsonResponse(data_dict, safe=False)  # Return JSON response
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response


class IncomeStatement(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        # Fetch the data
        stock = yf.Ticker(symbol)
        data = stock.financials

        # Extract the metrics we want
        selected_rows = data.loc[[
            "Total Revenue",
            "Operating Revenue",
            "Cost Of Revenue",
            "Gross Profit",
            "Operating Income",
            "Operating Expense",
            "Research And Development",
            "Selling General And Administration",
            "Interest Expense",
            "Interest Income",
            "Net Income",
            "EBIT",
            "EBITDA"
        ]]

        # Transpose the DataFrame and convert it to a dictionary
        dict_data = selected_rows.transpose().to_dict()

        # Convert the Timestamp keys to strings, keeping only the date portion, and divide all values by 1 million
        str_dict_data = {
            key: {
                inner_key.strftime('%Y-%m-%d') if isinstance(inner_key, pd.Timestamp) else inner_key: 
                int(value / 1_000_000) if not math.isnan(value) else None
                for inner_key, value in value.items()
            } 
            for key, value in dict_data.items()
        }

        # Convert the dictionary to a list of dictionaries in the desired format
        json_data = [{'item': key, **value} for key, value in str_dict_data.items()]

        # Return the data as a JSON response
        response = JsonResponse(json_data, safe=False)
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response
    

class BalanceSheet(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        # Fetch the data
        stock = yf.Ticker(symbol)
        data = stock.balance_sheet

        # Define the keys
        keys = [
            "Cash And Cash Equivalents", "Other Short Term Investments",
            "Cash Cash Equivalents And Short Term Investments", "Receivables",
            "Inventory", "Other Current Assets", "Current Assets",
            "Properties", "Machinery Furniture Equipment",
            "Long Term Equity Investment", "Other Intangible Assets",
            "Total Assets", "Accounts Payable", "Current Debt",
            "Other Current Liabilities", "Current Liabilities",
            "Long Term Debt", "Other Non Current Liabilities",
            "Total Non Current Liabilities Net Minority Interest",
            "Total Liabilities Net Minority Interest", "Common Stock",
            "Retained Earnings", "Total Equity", "Gross Minority Interest",
            "Total Debt", "Net Debt"
        ]

        # Initialize an empty DataFrame to store the selected rows
        selected_rows = pd.DataFrame(columns=data.columns, index=keys)

        # Select each row individually
        for key in keys:
            if key in data.index:
                selected_rows.loc[key] = data.loc[key]
            else:
                selected_rows.loc[key] = pd.Series([None] * len(data.columns), index=data.columns)

        # Transpose the DataFrame and convert it to a dictionary
        dict_data = selected_rows.transpose().to_dict()

        # Convert the Timestamp keys to strings, keeping only the date portion, and divide all values by 1 million
        str_dict_data = {
            key: {
                inner_key.strftime('%Y-%m-%d') if isinstance(inner_key, pd.Timestamp) else inner_key: 
                int(value / 1_000_000) if value is not None else None
                for inner_key, value in value.items()
            } 
            for key, value in dict_data.items()
        }
        
        # Convert the dictionary to a list of dictionaries in the desired format
        json_data = [{'item': key, **value} for key, value in str_dict_data.items()]

        # Return the data as a JSON response
        response = JsonResponse(json_data, safe=False)
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response
    

class CashFlow(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        # Fetch the data
        stock = yf.Ticker(symbol)
        data = stock.cashflow

        # Extract the metrics we want
        keys = [
            "Depreciation And Amortization", "Operating Cash Flow",
            "Net Other Investing Changes", "Capital Expenditure", "Investing Cash Flow",
            "Common Stock Issuance", "Cash Dividends Paid", "Common Stock Dividend Paid",
            "Financing Cash Flow", "Changes In Cash", "Free Cash Flow"
        ]

        # Initialize an empty DataFrame to store the selected rows
        selected_rows = pd.DataFrame(columns=data.columns, index=keys)

        # Select each row individually
        for key in keys:
            if key in data.index:
                selected_rows.loc[key] = data.loc[key]
            else:
                selected_rows.loc[key] = pd.Series([None] * len(data.columns), index=data.columns)

        # Transpose the DataFrame and convert it to a dictionary
        dict_data = selected_rows.transpose().to_dict()

        # Convert the Timestamp keys to strings, keeping only the date portion, and divide all values by 1 million
        str_dict_data = {
            key: {
                inner_key.strftime('%Y-%m-%d') if isinstance(inner_key, pd.Timestamp) else inner_key: 
                int(value / 1_000_000) if value is not None else None
                for inner_key, value in value.items()
            } 
            for key, value in dict_data.items()
        }
        
        # Convert the dictionary to a list of dictionaries in the desired format
        json_data = [{'item': key, **value} for key, value in str_dict_data.items()]

        # Return the data as a JSON response
        response = JsonResponse(json_data, safe=False)
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response


class PriceHistory(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        stock = yf.Ticker(symbol)
        data = stock.history(period='max')  # Fetch Price History
        data = data[['Close']]  # Only want to keep the closing price information
        data.index = data.index.strftime('%Y-%m-%d')  # Convert Timestamp to string

        response = JsonResponse(data.to_dict())  # Create the JsonResponse
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response


class AssetSummary(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")
        stock = yf.Ticker(symbol)
        info = stock.info
        data = {
            'trailingPE': info.get('trailingPE'),
            'forwardPE': info.get('forwardPE'),
            'trailingEps': info.get('trailingEps'),
            'forwardEps': info.get('forwardEps'),
            'earningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth'),
            'revenueGrowth': info.get('revenueGrowth'),
            'grossMargins': info.get('grossMargins'),
            'ebitdaMargins': info.get('ebitdaMargins'),
            'operatingMargins': info.get('operatingMargins'),
            'targetMeanPrice': info.get('targetMeanPrice'),
            'targetHighPrice': info.get('targetHighPrice'),
            'targetLowPrice': info.get('targetLowPrice'),
            'SandP52WeekChange': info.get('SandP52WeekChange'),
            'dividendRate': info.get('dividendRate'),
            'dividendYield': info.get('dividendYield'),
            'payoutRatio': info.get('payoutRatio'),
            'trailingAnnualDividendRate': info.get('trailingAnnualDividendRate'),
            'trailingAnnualDividendYield': info.get('trailingAnnualDividendYield'),
            'lastDividendValue': info.get('lastDividendValue'),
            'lastDividendDate': info.get('lastDividendDate'),
            'beta': info.get('beta'),
            'auditRisk': info.get('auditRisk'),
            'boardRisk': info.get('boardRisk'),
            'compensationRisk': info.get('compensationRisk'),
            'shareHolderRightsRisk': info.get('shareHolderRightsRisk'),
            'overallRisk': info.get('overallRisk')
        }
        response = JsonResponse(data)  # Create the JsonResponse
        response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
        return response
    

class AssetNews(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")

        api_key = os.getenv('NEWS_API_KEY')
        if api_key is None:
            return HttpResponseServerError("NEWS_API_KEY is not set.")

        response = requests.get('https://api.marketaux.com/v1/news/all', params={'symbols': symbol, 'language': 'en', "api_token": api_key, "filter_entities":"true"})
        if response.status_code == 200:
            data = response.json()
            response = JsonResponse(data)  # Create the JsonResponse
            response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
            return response
        else:
            return HttpResponseBadRequest('API request failed.')
        

class LogoImage(View):
    def get(self, request, *args, **kwargs):
        symbol = request.GET.get('symbol')
        if symbol is None:
            return HttpResponseBadRequest("The 'symbol' parameter is required.")

        api_key = os.getenv('LOGO_API_KEY')
        if api_key is None:
            return HttpResponseServerError("LOGO_API_KEY is not set.")

        headers = {'x-api-key': api_key}
        response = requests.get('https://api.api-ninjas.com/v1/logo', params={'ticker': symbol}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            response = JsonResponse(data, safe=False)  # Create the JsonResponse
            response["Access-Control-Allow-Origin"] = "*"  # Add the header to the response
            return response
        else:
            return HttpResponseBadRequest('API request failed.')