from flask import Flask, request, jsonify
from mt5_connector import initialize_mt5, shutdown_mt5, execute_trade, close_positions
from utils import log_info, log_error, validate_payload, replace_placeholders
from config import WEBHOOK_SECRET, FLASK_HOST, FLASK_PORT, NGROK_AUTH_TOKEN
from pyngrok import ngrok

# Start Ngrok to expose the Flask app
def start_ngrok():
    try:
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)
        public_url = ngrok.connect(FLASK_PORT).public_url
        log_info(f"Ngrok tunnel created: {public_url}")
        return public_url
    except Exception as e:
        log_error(f"Failed to start Ngrok: {str(e)}")
        raise

# Initialize Flask app
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Validate incoming JSON payload
        data = request.get_json()
        if not data:
            return {"error": "Empty payload"}, 400

        # Log the incoming action for debugging
        log_info(f"Received trade action: {data.get('action')}")

        # Validate webhook authentication
        if data.get('auth_token') != WEBHOOK_SECRET:
            return {"error": "Invalid authentication token"}, 403

        # Replace placeholders from TradingView alerts
        data = replace_placeholders(data)

        # Validate payload and execute trade
        validation_error = validate_payload(data)
        if validation_error:
            return validation_error

        # Initialize MT5 connection
        if not initialize_mt5():
            return {"error": "Failed to connect to MetaTrader 5"}, 500

        # ✅ Close opposite positions before executing the new trade
        if not close_positions(symbol=data['symbol'], action=data['action']):
            shutdown_mt5()
            return {"error": f"Failed to close opposite positions for {data['symbol']}"}, 500

        # Execute trade
        trade_result = execute_trade(
            symbol=data['symbol'],
            action=data['action'],
            lot_size=data['lot_size'],
            entry_price=float(data['entry_price']),
            stop_loss_points=data.get('stop_loss'),
            take_profit=None
        )

        # Shutdown MT5 after execution
        shutdown_mt5()

        return jsonify(trade_result)

    except Exception as e:
        log_error(f"Webhook error: {str(e)}")
        return {"error": "Internal server error"}, 500



# Start Ngrok and Flask app
if __name__ == "__main__":
    public_url = start_ngrok()
    log_info(f"Webhook listening at {public_url}/webhook")
    app.run(host=FLASK_HOST, port=FLASK_PORT)
