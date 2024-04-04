# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import time
import os
import requests
import json
from collections import OrderedDict
from portfolio.views import write_view_outputs_to_file
from .models import OpenAIFile 
from portfolio.models import Portfolio, Asset
from portfolio.views import create_portfolio, create_transaction
from openai import OpenAI
import yfinance as yf
from pypfopt import risk_models
from pypfopt import expected_returns
from pypfopt import EfficientFrontier
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
FMP_APIKEY = os.getenv("FMP_APIKEY")


@csrf_exempt
def post_new(request):
    print("Received request")
    if request.method == 'POST':
        print("Processing POST request")
        thread = client.beta.threads.create()
        print(f"Created thread with ID: {thread.id}")
        client.beta.threads.messages.create(
            thread_id=thread.id,
            content="Greet the user and tell it about yourself and ask it what it is looking for.",
            role="user",
            metadata={
                "type": "hidden"
            }
        )
        print("Created message in thread")
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        print(f"Created run with ID: {run.id}")
        
        while True:
            print("Waiting on run")
            run = wait_on_run(run, thread.id)
            print(f"Run status: {run.status}")
            if run.status == "completed":
                print("Run completed")
                messages = get_messages(thread.id)
                return JsonResponse({"messages": messages, "thread_id": thread.id, "run_id": run.id})
            else:
                print("Run not completed, sleeping for 0.5s")
                time.sleep(0.5)
                continue
    
    print("Received non-POST request")
    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)


@csrf_exempt
def chat(request, thread_id):
    if request.method == 'POST':

        # Define your function dispatch table here
        function_dispatch_table = {
            'get_asset_price': get_asset_price,
            'get_asset_info': get_asset_info,
            'get_news': get_news,
            'get_markettrends_and_news': get_markettrends_and_news,
            'google_search': google_search,
            "get_sector_performance": get_sector_performance,
            "optimise_portfolio": optimise_portfolio,
            "add_optimised_portfolio_to_app": add_optimised_portfolio_to_app,
        }

        content = json.loads(request.body)['content']
        run = submit_message(ASSISTANT_ID, thread_id, content)
        
        all_required_actions = []

        while True:
            run = wait_on_run(run, thread_id)

            if run.status == "completed":
                messages = get_messages(thread_id)
                return JsonResponse({"required_actions": all_required_actions, "messages": messages})

            elif run.status == "requires_action":
                required_actions = run.required_action.submit_tool_outputs.model_dump()
                all_required_actions.append(required_actions)
                tool_outputs = []
                for action in required_actions["tool_calls"]:
                    func_name = action["function"]["name"]
                    print("Calling function: ", func_name)
                    
                    try:
                        arguments = json.loads(action["function"]["arguments"])
                    except json.JSONDecodeError:
                        arguments = {}

                    func = function_dispatch_table.get(func_name)
                    if func:
                        result = func(**arguments)  # ** unpacks the dictionary into keyword arguments
                        output = json.dumps(result) if not isinstance(result, str) else result
                        tool_outputs.append(
                            {
                                "tool_call_id": action["id"],
                                "output": output,
                            }
                        )
                    else:
                        print(f"Function {func_name} not found in dispatch table")

                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                continue

            elif run.status == "cancelled":
                return JsonResponse({"messages": "Run was cancelled."}, status=400)
            
            elif run.status == "failed":
                return JsonResponse({"messages": "Run failed."}, status=400)

            else:
                # wait for 0.5s until run is completed or requires action
                time.sleep(0.5)
                continue

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

@csrf_exempt
def uploadfile_and_update(request, pid):
    if request.method == 'POST':
        create_portfolio_info_file(pid)

        #Upload the file to OpenAI
        file = client.files.create(
            file=open('chatbot/data/portfolio_data.txt', 'rb'), 
            purpose = "assistants"
        )

        # Save the file ID in the database
        openai_file = OpenAIFile(file_id=file.id)
        openai_file.save()

        #Update Assistant
        assistant = client.beta.assistants.update(
            ASSISTANT_ID,
            file_ids=[file.id]
        )

        return JsonResponse({"success": "File created successfully."})
    return JsonResponse({"error": "Unable to upload file."}, status=405)

@csrf_exempt
def delete_file(request):
    if OpenAIFile.objects.exists():
        file = OpenAIFile.objects.last()
        fid = file.file_id
        if request.method == 'POST':
            file_deletion_status = client.beta.assistants.files.delete(
                assistant_id=ASSISTANT_ID,
                file_id=fid
            ) #Delete the file from the assistant
            client.files.delete(fid)  # Delete the file from OpenAI storage
            file.delete()  # Delete the file ID from the database
            return JsonResponse({"success": "File deleted successfully: " + fid}, status=200)
    else:
        return JsonResponse({"error": "No file ID found in the database."}, status=404)

    return JsonResponse({"No files in database"}, status=200)


def submit_message(assistant_id, thread_id, user_message):
    client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=user_message
    )
    return client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )


def wait_on_run(run, thread_id):
    while run.status == "queued" or run.status == "in_progress":
        print("Inside wait on run")
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run


def get_messages(thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    result = [
        {
            "content": message.content[0].text.value,
            "role": message.role,
            "hidden": "type" in message.metadata and message.metadata["type"] == "hidden",
            "id": message.id,
            "created_at": message.created_at,
            "thread_id": thread_id
        }
        for message in messages.data
    ]

    return result



#########################################################################################################

def create_portfolio_info_file(pid):
    dir_path = os.path.join(settings.BASE_DIR, 'chatbot', 'data')
    file_path = os.path.join(dir_path, 'portfolio_data.txt')
    write_view_outputs_to_file(pid, file_path)

def get_news(topic):
    params = {
        "engine": "google",
        "tbm": "nws",
        "q": topic,
        "api_key": SERPAPI_API_KEY,
    }
    response = requests.get('http://serpapi.com/search', params=params)
    data = response.json()
    news = data.get('news_results')
    news_string = ""
    for news_item in news:
        if news_item:
            title = news_item.get('title', 'No title')
            snippet = news_item.get('snippet', 'No snippet')
            link = news_item.get('link', "No link")
            date = news_item.get('date', 'No date')
            news_string += f"Title: {title}\n"
            news_string += f"Snippet: {snippet}\n"
            news_string += f"Link: {link}\n"
            news_string += f"Date: {date}\n\n"
        else:
            print("Encountered None value in news data.")
    return news_string

def get_markettrends_and_news(topic):
    # Topics:
        #indexes
        #most-active
        #gainers
        #losers
        #climate-leaders
        #cryptocurrencies
        #currencies
    
    params = {
        "engine": "google_finance_markets",
        "hl": "en",
        "trend": topic,
        "api_key": SERPAPI_API_KEY,
    }
    response = requests.get('http://serpapi.com/search', params=params)
    data = response.json()
    
    if topic == "Market-indexes":
        market_trends = data.get('market_trends')
    else:
        market_trends_data = data.get('market_trends')
        if market_trends_data is not None:
            trends = market_trends_data[0]
            results = trends.get('results')[:10]
            for result in results:
                # Remove the "serpapi_link", "link", and "extracted_price" fields if they exist
                result.pop("serpapi_link", None)
                result.pop("link", None)
                result.pop("extracted_price", None)

            market_trends = {
                "title": trends.get("title"),
                "subtitle": trends.get("subtitle"),
                "results": results
            }
        else:
            market_trends = "Nothing to show yet, Market trends are usually available within 15 minutes of local market opening."

    market_trends_and_news = {
        "trends": market_trends,
        "news": data.get('news_results')
    }
    
    return market_trends_and_news

def get_asset_info(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info
    data = {
        "General": {
            'company_name': info.get('longName'),
            'price': f"{info.get('regularMarketOpen'):.2f}",
            'ticker': info.get('symbol'),
            'country': info.get('country'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'quoteType': info.get('quoteType'),
            'exchange': info.get('exchange'),
            'about': info.get('longBusinessSummary'),
            'marketCap': info.get('marketCap'),
        },
        "Valuation Metrics":{
            'trailingPE': info.get('trailingPE'),
            'forwardPE': info.get('forwardPE'),
            'trailingEps': info.get('trailingEps'),
            'forwardEps': info.get('forwardEps'),
        },
        "Growth":{
            'earningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth'),
            'revenueGrowth': info.get('revenueGrowth'),
            'grossMargins': info.get('grossMargins'),
            'ebitdaMargins': info.get('ebitdaMargins'),
            'operatingMargins': info.get('operatingMargins'),
        },
        "Forecast":{
            'targetMeanPrice': info.get('targetMeanPrice'),
            'targetHighPrice': info.get('targetHighPrice'),
            'targetLowPrice': info.get('targetLowPrice'),
            'SandP52WeekChange': info.get('SandP52WeekChange')
        },
        "Dividends": {
            'dividendRate': info.get('dividendRate'),
            'dividendYield': info.get('dividendYield'),
            'payoutRatio': info.get('payoutRatio'),
            'trailingAnnualDividendRate': info.get('trailingAnnualDividendRate'),
            'trailingAnnualDividendYield': info.get('trailingAnnualDividendYield'),
            'lastDividendValue': info.get('lastDividendValue'),
            'lastDividendDate': info.get('lastDividendDate')
        },
        "Risk": {
            'beta': info.get('beta'),
            'auditRisk': info.get('auditRisk'),
            'boardRisk': info.get('boardRisk'),
            'compensationRisk': info.get('compensationRisk'),
            'shareHolderRightsRisk': info.get('shareHolderRightsRisk'),
            'overallRisk': info.get('overallRisk')
        }
    }

    return data

def get_asset_price(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info
    price=info.get('regularMarketOpen')
    data = str(price) + " USD"
    return data

def google_search(query):
    params = {
        "engine": "google",
        "q": query,
        "gl": "sg",
        "hl": "en",
        "api_key": SERPAPI_API_KEY,
    }
    response = requests.get('http://serpapi.com/search', params=params)
    data = response.json()

    result = {}

    if data.get('answer_box'):
        ab = {
            "title": data['answer_box'].get('title'),
            "answer": data['answer_box'].get('answer'),
            "snippet": data['answer_box'].get('snippet'),
            "snippet_highlighted_words": data['answer_box'].get('snippet_highlighted_words')
        }
        result['answer_box'] = ab

    if data.get('knowledge_graph'):
        kg = {
            "title": data['knowledge_graph'].get('title'),
            "type": data['knowledge_graph'].get('type'),
            "description": data['knowledge_graph'].get('description'),
        }
        result['knowledge_graph'] = kg

    return result

def get_sector_performance():
    url = "https://financialmodelingprep.com/api/v3/sector-performance?"
    params = {
        "apikey": FMP_APIKEY
    }
    response = requests.get(url, params=params)

    return response.json()

def optimise_portfolio(pid, method = "max_sharpe" ):
    try:
        portfolio = Portfolio.objects.get(id=pid)
    except ObjectDoesNotExist:
        return {"error": "Unable to optimise, portfolio not found."}
    assets = Asset.objects.filter(portfolio=portfolio)

    if assets.count() < 2:
        return "Unable to optimise, add more assets to the portfolio."

    # Obtain Price Of Each Asset And Calculate Total Portfolio Value
    portfolio_value = 0
    price_dict = {}
    tickers = []
    for asset in assets:
        price = yf.Ticker(asset.ticker).info.get('regularMarketOpen')
        value = round(float(price) * float(asset.units), 2)
        portfolio_value += value
        price_dict[asset.ticker.upper()] = price  # Convert key to uppercase directly
        tickers.append(asset.ticker)

    portfolio_value = round(portfolio_value, 2)
    # Order price_dict by keys
    price_dict = OrderedDict(sorted(price_dict.items()))
    
    # Perform Mean Variance Optimisation
    ohlc = yf.download(tickers, period="max")
    prices = ohlc["Adj Close"].dropna()
    prices = prices.dropna()

    S = risk_models.CovarianceShrinkage(prices).ledoit_wolf()
    mu = expected_returns.capm_return(prices)
    ef = EfficientFrontier(mu, S)
    if method == "min_volatility":
        ef.min_volatility()
    else:
        ef.max_sharpe()
    weights = ef.clean_weights() #Remove negligibles
    expected_return, volatility, sharpe_ratio = ef.portfolio_performance(verbose=True)

    # Calculate Units of Each Asset To Buy
    sum = 0
    for key in weights:
        weights[key] = weights[key] * portfolio_value
        sum += weights[key]
        weights[key] = float(format(weights[key] / price_dict[key], '.3g'))
        
    #Calculate Balance
    portfolio_balance = portfolio_value - sum  

    return {
        "Units of each asset": weights,
        "Annual expected_return": f"{expected_return:.2f}",
        "Volatility": f"{volatility:.2f}",
        "Sharpe_ratio": f"{sharpe_ratio:.2f}",
        "Capital": f"{portfolio_value} USD",  
        "Amount used": f"{sum:.2f} USD",
        "Balance": f"{portfolio_balance:.2f} USD"
    }

def add_optimised_portfolio_to_app(allocations, uid):
    print(allocations)
    try:
        # Create a portfolio
        portfolio_id = create_portfolio(uid, 'Optimised Portfolio', '-')
        print(f"Created portfolio with ID {portfolio_id}")

        # Iterate over allocations and create a transaction for each asset
        for allocation in allocations:
            # Get stock information
            stock = yf.Ticker(allocation['asset_ticker'])
            info = stock.info
            asset_name = info.get('longName')
            asset_ticker = allocation['asset_ticker']
            asset_type = info.get('quoteType', 'Others')
            asset_sector = info.get('sector', 'Others')
            price = info.get('regularMarketOpen')
            units = allocation['units']

            print(f"Creating transaction for asset {asset_name} ({asset_ticker})")

            # Create a transaction
            create_transaction(portfolio_id, 'buy', asset_name, asset_ticker, asset_type, asset_sector, units, price)

            print(f"Created transaction for asset {asset_name} ({asset_ticker})")

        # If everything went well, return a success message
        return "Successfully added optimised portfolio to app."

    except Exception as e:
        # If something went wrong, return the error message
        print(f"Caught exception: {str(e)}")
        return f"Something went wrong: {str(e)}"
