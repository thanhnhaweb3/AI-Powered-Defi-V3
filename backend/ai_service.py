from openai import OpenAI
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from dotenv import load_dotenv
import os
import logging
import requests
import re
from auto_deposit import AutoDepositService
from defi_service import DeFiService

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        try:
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise

        try:
            self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            logger.info("Anthropic client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            raise

        try:
            self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
            self.deepseek_endpoint = "https://api.deepseek.com/v1/chat/completions"
            if not self.deepseek_api_key:
                raise ValueError("DeepSeek API key is missing")
            logger.info("DeepSeek client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek client: {str(e)}")
            raise

        self.auto_deposit = AutoDepositService()
        self.defi_service = DeFiService()

    def extract_amount(self, question: str) -> int:
        match = re.search(r'(\d+)', question)
        return int(match.group(1)) if match else 10

    def ask_question(self, question: str, model: str = "anthropic", user_id: str = None) -> str:
        logger.info(f"Processing question: '{question}' with model: {model} for user: {user_id}")
        
        if model == "openai":
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": question}],
                    max_tokens=500
                )
                return response.choices[0].message.content
            except Exception as e:
                raise Exception(f"OpenAI error: {str(e)}")

        elif model == "anthropic":
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=500,
                    messages=[{"role": "user", "content": f"{HUMAN_PROMPT}{question}{AI_PROMPT}"}]
                )
                return response.content[0].text
            except Exception as e:
                raise Exception(f"Anthropic error: {str(e)}")

        elif model == "deepseek":
            try:
                question_lower = question.lower()
                user_wallet, _ = self.defi_service.get_wallet(user_id)
                if not user_wallet:
                    return "Please create an AA Wallet first using 'create_aa_wallet' action."

                amount = self.extract_amount(question)

                if "deposit" in question_lower and "usdc" in question_lower:
                    transfer_result = self.defi_service.transfer_usdc_from_user(user_id, amount)
                    deposit_result = self.auto_deposit.deposit_usdc_to_uniswap(amount)
                    return f"Deposited {amount} USDC to Uniswap pool. Tx hash: {deposit_result['tx_hash']}"

                elif "swap" in question_lower and "usdc" in question_lower:
                    transfer_result = self.defi_service.transfer_usdc_from_user(user_id, amount)
                    swap_result = self.auto_deposit.deposit_usdc_to_uniswap(amount)
                    return f"Swapped {amount} USDC to WETH. Tx hash: {swap_result['tx_hash']}"

                elif "transfer" in question_lower and "usdc" in question_lower:
                    transfer_result = self.auto_deposit.transfer_usdc_to_user(amount, user_wallet)
                    return f"Transferred {amount} USDC back to your wallet. Tx hash: {transfer_result['tx_hash']}"

                elif "withdraw" in question_lower and "usdc" in question_lower:
                    withdraw_result = self.auto_deposit.withdraw_usdc_from_aave(amount, user_wallet)
                    return f"Withdrawn {amount} USDC from Aave to your wallet. Tx hash: {withdraw_result['tx_hash']}"

                headers = {"Authorization": f"Bearer {self.deepseek_api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": question}],
                    "max_tokens": 500,
                    "temperature": 1.0
                }
                response = requests.post(self.deepseek_endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.HTTPError as e:
                raise Exception(f"DeepSeek API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"DeepSeek error: {str(e)}")

        else:
            raise ValueError(f"Unsupported model: {model}")
