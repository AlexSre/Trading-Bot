import MetaTrader5 as mt5
from utils import log_error, log_info
import time

def initialize_mt5():
    """Initialize the MT5 connection."""
    if not mt5.initialize():
        log_error("Failed to initialize MT5")
        return False

    account_info = mt5.account_info()
    if account_info is None:
        log_error("Failed to get account info")
        return False

    log_info(f"Logged in as {account_info.name} (Balance: {account_info.balance})")
    return True


def shutdown_mt5():
    """Shut down the MT5 connection."""
    mt5.shutdown()
    log_info("MT5 connection closed")


def execute_trade(symbol, action, lot_size, entry_price, stop_loss_points=None, take_profit=None):
    """Execute a trade with dynamic stop loss calculation and no take profit."""
    try:
        # Ensure the symbol is available for trading
        if not mt5.symbol_select(symbol, True):
            log_error(f"Symbol {symbol} is not available for trading.")
            return {"error": f"Symbol {symbol} is not available for trading."}

        # Get current price info
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info or not symbol_info.visible:
            log_error(f"Symbol {symbol} is invalid or not visible.")
            return {"error": f"Invalid symbol: {symbol}"}

        price_info = mt5.symbol_info_tick(symbol)
        if not price_info:
            log_error(f"Failed to retrieve price information for {symbol}.")
            return {"error": f"Failed to retrieve price information for {symbol}."}

        # Correct action mapping
        if action.lower() == "buy":
            order_type = mt5.ORDER_TYPE_BUY
            current_price = price_info.ask
        elif action.lower() == "sell":
            order_type = mt5.ORDER_TYPE_SELL
            current_price = price_info.bid
        else:
            return {"error": "Invalid action. Must be 'buy' or 'sell'."}

        # Calculate stop loss price
        sl_price = None
        if stop_loss_points:
            point = symbol_info.point
            if order_type == mt5.ORDER_TYPE_BUY:
                sl_price = entry_price - stop_loss_points * point
            else:
                sl_price = entry_price + stop_loss_points * point

        # Create the trade request
        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": current_price,
            "sl": sl_price,
            "tp": take_profit if take_profit is not None else 0.0,
            "deviation": 20,
            "magic": 123456,
            "comment": f"Webhook trade: {action} {symbol}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        log_info(f"Trade request: {trade_request}")

        # Attempt to send the trade request up to 3 times
        for attempt in range(3):
            result = mt5.order_send(trade_request)
            if result is None:
                log_error(f"MT5 order_send() returned None. Error: {mt5.last_error()}")
                continue

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                log_info(f"Trade executed successfully: {result}")
                return {"success": True, "result": result._asdict()}

            log_error(f"Trade failed. Attempt {attempt + 1}/3. Code: {result.retcode}, Error: {mt5.last_error()}")

        return {"error": "Trade execution failed after 3 attempts."}

    except Exception as e:
        log_error(f"Trade execution error: {str(e)}")
        return {"error": str(e)}





import time

def close_positions(symbol, action):
    """Close opposite positions before opening a new trade with retry logic."""
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        log_info(f"No open positions found for {symbol}")
        return True  # No positions to close

    for position in positions:
        if position.type != (mt5.ORDER_TYPE_BUY if action == "buy" else mt5.ORDER_TYPE_SELL):
            # Ensure valid price data
            tick_info = mt5.symbol_info_tick(symbol)
            if not tick_info:
                log_error(f"Failed to retrieve tick info for {symbol}")
                return False

            # Get current price for closing position
            price = tick_info.bid if position.type == mt5.ORDER_TYPE_BUY else tick_info.ask

            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": position.ticket,
                "price": price,
                "deviation": 50,  # Increase deviation to handle slippage
                "magic": position.magic,
                "comment": "Closed by bot",
            }

            log_info(f"Close request: {close_request}")

            # Retry position closure up to 3 times with exponential backoff
            for attempt in range(3):
                result = mt5.order_send(close_request)

                if result is None:
                    log_error("MT5 order_send() returned None. Retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue

                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    log_info(f"Position closed successfully: {result}")
                    break

                log_error(f"Failed to close position. Attempt {attempt + 1}/3. Code: {result.retcode}, Error: {mt5.last_error()}")
                time.sleep(2 ** attempt)  # Exponential backoff

                # Return False if all attempts fail
                if attempt == 2:
                    return False

    return True


