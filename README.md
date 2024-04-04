# Description

This is the Django backend code for BucksBuddy, an investment portfolio management application with a GPT chatbot. This project is part of my final year project.

The backend is organized into several Django apps, each handling different functionalities:

- `accounts`: Handles user accounts and authentication.
- `asset`: Manages asset information retrieval functionality.
- `portfolio`: Handles the portfolio management functionality.
- `chatbot`: Manages the GPT chatbot functionality.
- `core`: Handles core functionalities of the backend.


## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/FunkyQai/BucksBuddyBackEnd.git
    ```

2. Navigate to the project directory:
    ```bash
    cd BucksBuddyBackEnd
    ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```


## Configuration

Create a `.env` file in the root directory of the project and add the following keys:

```properties
NEWS_API_KEY=
LOGO_API_KEY=
OPENAI_API_KEY=
ASSISTANT_ID=
FMP_APIKEY=
SERPAPI_API_KEY=
```

You can obtain these keys from the following sources:

NEWS_API_KEY: [News API](https://www.marketaux.com/)

LOGO_API_KEY: [Logo API](https://api-ninjas.com/)

OPENAI_API_KEY: [OpenAI](https://openai.com/)

ASSISTANT_ID: [IBM Watson Assistant](https://platform.openai.com/playground)

FMP_APIKEY: [Financial Modeling Prep API](https://site.financialmodelingprep.com/developer/docs)

SERPAPI_API_KEY: [SERP API](https://www.searchapi.io/?gad_source=1&gclid=Cj0KCQjwn7mwBhCiARIsAGoxjaJoo6bl1kYLjjjMIIw3NgVwbDFpTLHCk_b-rIpGdHDh94aa2hsiMMUaAo3PEALw_wcB)



## Running the Application

To run the application, use the following command:
    ```bash
    python manage.py runserver
    ```


## Frontend

Run the Frontend code as well which can be found in this repository:
https://github.com/FunkyQai/BucksBuddyFrontEnd.git
