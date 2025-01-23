import logging
import os
import re

# Ensure logs directory exists
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=f"{log_dir}/trading_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# Logging functions
def log_info(message):
    logging.info(message)

def log_error(message):
    logging.error(message)

# Replace placeholders in the payload
def replace_placeholders(data):
    if isinstance(data, dict):
        return {k: replace_placeholders(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_placeholders(v) for v in data]
    elif isinstance(data, str):
        placeholder_values = {
            "strategy.order.action": "buy",
            "strategy.order.alert_message": "Supertrend Buy Signal",
            "order.id": "12345",
            "close": "1.02983"
        }
        return re.sub(r"{{(.*?)}}", lambda m: placeholder_values.get(m.group(1), m.group(0)), data)
    else:
        return data

# Validate payload structure
def validate_payload(data):
    required_fields = ["auth_token", "symbol", "action", "lot_size", "stop_loss"]
    for field in required_fields:
        if field not in data:
            return {"error": f"Missing field: {field}"}, 400
    return None
