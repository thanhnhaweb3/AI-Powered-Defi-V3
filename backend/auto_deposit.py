from defi_service import DeFiService
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoDepositService:
    def __init__(self):
        self.defi_service = DeFiService()
        self.ai_wallet_address = self.defi_service.ai_wallet_address

    def deposit_usdc_to_uniswap(self, amount_usdc: int) -> dict:
        try:
            _, nonce = self.defi_service.get_wallet("AI_AGENT_WALLET")
            approve_user_op = self.defi_service.create_user_op(self.ai_wallet_address, "approve", amount_usdc, nonce)
            approve_result = self.defi_service.send_to_bundler(approve_user_op)
            if "error" in approve_result:
                raise Exception(approve_result["error"])
            logger.info(f"Approved Uniswap to spend {amount_usdc} USDC: {approve_result.get('result')}")
            self.defi_service.update_nonce("AI_AGENT_WALLET", nonce + 1)

            nonce += 1
            swap_user_op = self.defi_service.create_user_op(self.ai_wallet_address, "swap", amount_usdc, nonce)
            swap_result = self.defi_service.send_to_bundler(swap_user_op)
            if "error" in swap_result:
                raise Exception(swap_result["error"])
            logger.info(f"Swapped {amount_usdc} USDC to WETH: {swap_result.get('result')}")
            self.defi_service.update_nonce("AI_AGENT_WALLET", nonce + 1)

            return {"tx_hash": swap_result.get("result", "pending"), "status": "success"}
        except Exception as e:
            logger.error(f"Failed to deposit USDC to Uniswap: {str(e)}")
            raise Exception(f"Deposit error: {str(e)}")

    def supply_usdc_to_aave(self, amount_usdc: int) -> dict:
        try:
            _, nonce = self.defi_service.get_wallet("AI_AGENT_WALLET")
            supply_user_op = self.defi_service.create_user_op(self.ai_wallet_address, "supply", amount_usdc, nonce)
            supply_result = self.defi_service.send_to_bundler(supply_user_op)
            if "error" in supply_result:
                raise Exception(supply_result["error"])
            logger.info(f"Supplied {amount_usdc} USDC to Aave: {supply_result.get('result')}")
            self.defi_service.update_nonce("AI_AGENT_WALLET", nonce + 1)
            return {"tx_hash": supply_result.get("result", "pending"), "status": "success"}
        except Exception as e:
            logger.error(f"Failed to supply USDC to Aave: {str(e)}")
            raise Exception(f"Supply error: {str(e)}")

    def transfer_usdc_to_user(self, amount_usdc: int, recipient: str) -> dict:
        try:
            _, nonce = self.defi_service.get_wallet("AI_AGENT_WALLET")
            transfer_user_op = self.defi_service.create_user_op(self.ai_wallet_address, "transfer", amount_usdc, nonce, recipient)
            transfer_result = self.defi_service.send_to_bundler(transfer_user_op)
            if "error" in transfer_result:
                raise Exception(transfer_result["error"])
            logger.info(f"Transferred {amount_usdc} USDC to {recipient}: {transfer_result.get('result')}")
            self.defi_service.update_nonce("AI_AGENT_WALLET", nonce + 1)
            return {"tx_hash": transfer_result.get("result", "pending"), "status": "success"}
        except Exception as e:
            logger.error(f"Failed to transfer USDC: {str(e)}")
            raise Exception(f"Transfer error: {str(e)}")

    def withdraw_usdc_from_aave(self, amount_usdc: int, recipient: str) -> dict:
        try:
            _, nonce = self.defi_service.get_wallet("AI_AGENT_WALLET")
            withdraw_user_op = self.defi_service.create_user_op(self.ai_wallet_address, "withdraw", amount_usdc, nonce, recipient)
            withdraw_result = self.defi_service.send_to_bundler(withdraw_user_op)
            if "error" in withdraw_result:
                raise Exception(withdraw_result["error"])
            logger.info(f"Withdrawn {amount_usdc} USDC from Aave to {recipient}: {withdraw_result.get('result')}")
            self.defi_service.update_nonce("AI_AGENT_WALLET", nonce + 1)
            return {"tx_hash": withdraw_result.get("result", "pending"), "status": "success"}
        except Exception as e:
            logger.error(f"Failed to withdraw USDC from Aave: {str(e)}")
            raise Exception(f"Withdraw error: {str(e)}")
