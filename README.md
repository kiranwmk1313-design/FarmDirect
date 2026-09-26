# FarmDirect

FarmDirect is a small academic **farmer-to-buyer marketplace** built with Python Flask, SQLite, HTML/CSS/JavaScript and Bootstrap 5.

## Features
- Farmer and Buyer registration/login
- Role-based dashboards
- Farmer product add/edit/delete
- Search and category filtering
- Product details and stock quantity
- Buyer ordering / mock checkout
- Order history and farmer order-status updates
- Profile editing
- Password hashing and basic validation
- Responsive agricultural-themed UI
- Automatic SQLite database initialization
- Demo accounts and sample products

## Run in VS Code

1. Install Python 3.10+.
2. Open this folder in VS Code.
3. Open Terminal.
4. Create an environment:
   `python -m venv venv`
5. Activate it on Windows:
   `venv\Scripts\activate`
6. Install dependencies:
   `pip install -r requirements.txt`
7. Start:
   `python app.py`
8. Open `http://127.0.0.1:5000`

## Demo accounts
Farmer: `farmer@farmdirect.com` / `farmer123`
Buyer: `buyer@farmdirect.com` / `buyer123`

The project is intended as a presentable MVP/demo. Checkout is simulated; no real payment gateway is connected.
