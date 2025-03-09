from fastapi import FastAPI, HTTPException
import logging
from ai_service import AIService
from defi_service import DeFiService
from credit_service import CreditService
from stripe_service import StripeService
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_service = AIService()
defi_service = DeFiService()
credit_service = CreditService()
stripe_service = StripeService()

# Khởi tạo scheduler
scheduler = BackgroundScheduler()

def check_all_users_profits():
    """Kiểm tra lợi nhuận của tất cả user có vị thế active."""
    try:
        users = defi_service.db.fetch_all("SELECT DISTINCT user_id FROM wallets")
        for user in users:
            user_id = user[0]
            logger.info(f"Checking profits for user: {user_id}")
            defi_service.check_and_withdraw(user_id)
    except Exception as e:
        logger.error(f"Error in scheduled profit check: {str(e)}")

# Thêm scheduler khi ứng dụng khởi động
@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(
        check_all_users_profits,
        trigger=IntervalTrigger(minutes=15),  # Kiểm tra mỗi 15 phút
        id="check_profits",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started for profit checking every 15 minutes")

# Tắt scheduler khi ứng dụng dừng
@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler shut down")

@app.post("/ai_credit_endpoint")
async def endpoint(request: dict):
    action = request.get("action")
    user_id = request.get("user_id")
    logger.info(f"Received request: action={action}, user_id={user_id}")

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        if action == "credits":
            credits = credit_service.check_credits(user_id)
            return {"credits_remaining": credits}

        elif action == "get_aa_wallet":
            wallet_address, nonce = defi_service.get_wallet(user_id)
            bytecode = defi_service.w3.eth.get_code(wallet_address).hex() if wallet_address else None
            return {"wallet_address": wallet_address, "bytecode": bytecode}

        elif action == "create_aa_wallet":
            wallet_address = defi_service.create_aa_wallet(user_id)
            return {"wallet_address": wallet_address}

        elif action == "fund_ai_wallet":
            amount_eth = float(request.get("amount_eth", 0))
            if amount_eth <= 0:
                raise ValueError("Invalid amount_eth")
            result = defi_service.fund_ai_wallet(user_id, amount_eth)
            return result

        elif action == "swap":
            amount_in = int(request.get("amount_in", 0))
            if amount_in <= 0:
                raise ValueError("Invalid amount_in")
            return defi_service.swap_usdc_to_eth(amount_in, user_id)

        elif action == "supply":
            amount = int(request.get("amount", 0))
            if amount <= 0:
                raise ValueError("Invalid amount")
            return defi_service.supply_usdc(amount, user_id)

        elif action == "ask":
            question = request.get("question")
            model = request.get("model", "anthropic")
            if not question:
                raise ValueError("question is required")
            if not credit_service.deduct_credits(user_id, model):
                raise ValueError("Insufficient credits")
            response = ai_service.ask_question(question, model, user_id)
            return {"response": response}

        elif action == "buy_credits":
            amount = int(request.get("amount", 0))
            if amount <= 0:
                raise ValueError("Invalid amount")
            payment_intent = stripe_service.create_payment_intent(amount, user_id)
            return {
                "client_secret": payment_intent["client_secret"],
                "payment_intent_id": payment_intent["id"],
                "credits_to_add": amount
            }

        elif action == "confirm_buy_credits":
            payment_intent_id = request.get("payment_intent_id")
            credits_to_add = int(request.get("credits_to_add", 0))
            if not payment_intent_id or credits_to_add <= 0:
                raise ValueError("Invalid payment_intent_id or credits_to_add")
            if not stripe_service.confirm_payment(payment_intent_id):
                raise ValueError("Payment not completed")
            credit_service.add_credits(user_id, credits_to_add)
            return {"status": "success"}

        elif action == "check_profits":
            # Lấy tất cả vị thế active của user
            positions = defi_service.db.fetch_all(
                "SELECT position_id, platform, initial_value_usd FROM positions WHERE user_id = ? AND status = 'active'",
                (user_id,)
            )
            if not positions:
                return {"status": "no_active_positions"}

            results = []
            for position_id, platform, initial_value_usd in positions:
                # Tính giá trị hiện tại và profit ratio
                if platform == "aave":
                    current_value = defi_service.get_aave_position_value(user_id, position_id)
                elif platform == "uniswap":
                    current_value = defi_service.get_uniswap_position_value(user_id, position_id)
                else:
                    continue

                profit_ratio = current_value / initial_value_usd
                position_info = {
                    "position_id": position_id,
                    "platform": platform,
                    "initial_value_usd": initial_value_usd,
                    "current_value_usd": current_value,
                    "profit_ratio": profit_ratio,
                    "action_taken": None
                }

                # Kiểm tra và rút vốn nếu cần
                if profit_ratio >= 1.05 or profit_ratio <= 0.99:
                    wallet_address, nonce = defi_service.get_wallet(user_id)
                    if not wallet_address:
                        raise Exception("AA wallet not found for user")
                    
                    if platform == "aave":
                        user_op = defi_service.create_user_op(wallet_address, "withdraw", int(initial_value_usd), nonce, wallet_address)
                    elif platform == "uniswap":
                        user_op = defi_service.create_user_op(wallet_address, "transfer", int(initial_value_usd), nonce, wallet_address)
                    
                    result = defi_service.send_to_bundler(user_op)
                    if "error" in result:
                        position_info["action_taken"] = f"Failed to withdraw: {result['error']}"
                    else:
                        defi_service.update_nonce(user_id, nonce + 1)
                        defi_service.db.execute(
                            "UPDATE positions SET status = 'closed' WHERE position_id = ?", (position_id,)
                        )
                        position_info["action_taken"] = f"Withdrawn (Tx hash: {result.get('result', 'pending')})"
                        logger.info(f"Withdrawn {platform} position {position_id} for {user_id}. Profit ratio: {profit_ratio}")
                else:
                    position_info["action_taken"] = "No action needed"

                results.append(position_info)

            return {"status": "checked", "positions": results}

        else:
            raise ValueError(f"Invalid action: {action}")

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
