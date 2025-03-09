from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import Web3Exception
from dotenv import load_dotenv
import os
import json
import requests
import boto3
from database import Database
import logging
from eth_account.messages import encode_defunct
import time
from typing import Dict, Tuple, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import aiohttp  # Thêm để tối ưu hóa HTTP requests bất đồng bộ

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeFiService:
    def __init__(self, max_retries: int = 3):
        """Khởi tạo DeFiService với retry mechanism cho kết nối Web3."""
        self.rpc_url = os.getenv("ALCHEMY_RPC_URL")
        if not self.rpc_url:
            raise ValueError("ALCHEMY_RPC_URL not set in .env")
        
        self.w3 = self._initialize_web3(max_retries)
        self._setup_contracts_and_addresses()
        self.db = Database("wallets.db")
        self.ai_agent_address = Web3.to_checksum_address(self.w3.eth.account.from_key(os.getenv("AI_AGENT_PRIVATE_KEY")).address)
        self.ai_wallet_address = self.create_ai_wallet()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), 
           retry=retry_if_exception_type(Web3Exception))
    def _initialize_web3(self, max_retries: int) -> Web3:
        """Khởi tạo Web3 với retry khi kết nối thất bại."""
        w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # Hỗ trợ mạng PoA như Base
        if not w3.is_connected():
            logger.error(f"Failed to connect to Ethereum network at {self.rpc_url}")
            raise Web3Exception("Failed to connect to Ethereum network")
        logger.info(f"Connected to Ethereum network: {self.rpc_url}")
        return w3

    def _setup_contracts_and_addresses(self) -> None:
        """Thiết lập các địa chỉ và ABI contract."""
        self.kms_client = boto3.client(
            'kms',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name='us-east-1'
        )
        self.kms_key_id = os.getenv("KMS_KEY_ID")
        self.bundler_url = os.getenv("BUNDLER_URL")

        self.entry_point = Web3.to_checksum_address("0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789")
        self.factory_address = Web3.to_checksum_address("0x9406Cc6185a346906296840746125a0E44976454")
        self.usdc_address = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        self.weth_address = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
        self.uniswap_router = Web3.to_checksum_address("0x2626664c2603336E57B271c5C0b26F421741e481")
        self.aave_pool = Web3.to_checksum_address("0x0D535C2Be9b8522D8C58e614fe090cC9F628A9a9")

        # ABI cho các contract
        self.factory_abi = json.loads('''[
            {"inputs":[{"name":"owner","type":"address"},{"name":"salt","type":"uint256"}],"name":"createAccount","outputs":[{"name":"ret","type":"address"}],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"name":"owner","type":"address"},{"name":"salt","type":"uint256"}],"name":"getAddress","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"}
        ]''')
        self.uniswap_abi = json.loads('''[
            {"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}
        ]''')
        self.aave_abi = json.loads('''[
            {"inputs":[{"internalType":"address","name":"asset","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address","name":"onBehalfOf","type":"address"},{"internalType":"uint16","name":"referralCode","type":"uint16"}],"name":"supply","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"address","name":"asset","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address","name":"to","type":"address"}],"name":"withdraw","outputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}
        ]''')
        self.wallet_abi = json.loads('''[
            {"inputs":[{"internalType":"address","name":"dest","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"bytes","name":"func","type":"bytes"}],"name":"execute","outputs":[],"stateMutability":"nonpayable","type":"function"}
        ]''')
        self.usdc_abi = json.loads('''[
            {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
            {"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}
        ]''')

    def get_wallet(self, user_id: str) -> Tuple[Optional[str], int]:
        """Lấy địa chỉ ví và nonce từ database."""
        result = self.db.fetch_one("SELECT wallet_address, nonce FROM wallets WHERE user_id = ?", (user_id,))
        return result if result else (None, 0)

    def save_wallet(self, user_id: str, wallet_address: str) -> None:
        """Lưu ví vào database."""
        self.db.execute("INSERT OR REPLACE INTO wallets (user_id, wallet_address, nonce) VALUES (?, ?, ?)", 
                       (user_id, Web3.to_checksum_address(wallet_address), 0))

    async def create_aa_wallet(self, user_id: str) -> str:
        """Tạo hoặc lấy ví AA cho user_id bất đồng bộ."""
        wallet_address, _ = self.get_wallet(user_id)
        if wallet_address:
            return wallet_address

        factory_contract = self.w3.eth.contract(address=self.factory_address, abi=self.factory_abi)
        owner = self.ai_agent_address
        salt = int(self.w3.keccak(text=user_id).hex(), 16) % 2**256
        
        predicted_address = factory_contract.functions.getAddress(owner, salt).call()
        code = self.w3.eth.get_code(predicted_address)

        if code == b'\x00':
            tx = factory_contract.functions.createAccount(owner, salt).build_transaction({
                'from': self.ai_agent_address,
                'nonce': await self._get_nonce_async(self.ai_agent_address),
                'gas': 200000,
                'maxFeePerGas': self.w3.to_wei('2', 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei('1', 'gwei')
            })
            signed_tx = self.w3.eth.account.sign_transaction(tx, os.getenv("AI_AGENT_PRIVATE_KEY"))
            tx_hash = await self._send_raw_transaction_async(signed_tx.raw_transaction)
            receipt = await self._wait_for_receipt_async(tx_hash)
            logger.info(f"Created AA wallet for {user_id}: {predicted_address} - Tx: {tx_hash.hex()}")

        self.save_wallet(user_id, predicted_address)
        return predicted_address

    def create_ai_wallet(self) -> str:
        """Tạo ví AA cho AI agent (đồng bộ để dùng trong __init__)."""
        import asyncio
        return asyncio.run(self.create_aa_wallet("AI_AGENT_WALLET"))

    async def _get_nonce_async(self, address: str) -> int:
        """Lấy nonce bất đồng bộ."""
        return self.w3.eth.get_transaction_count(address)

    async def _send_raw_transaction_async(self, raw_tx: bytes) -> bytes:
        """Gửi giao dịch bất đồng bộ."""
        return self.w3.eth.send_raw_transaction(raw_tx)

    async def _wait_for_receipt_async(self, tx_hash: bytes) -> Dict:
        """Chờ receipt bất đồng bộ."""
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    async def fund_ai_wallet(self, user_id: str, amount_eth: float) -> Dict[str, str]:
        """Chuyển ETH từ ví user sang ví AI bất đồng bộ."""
        user_wallet, nonce = self.get_wallet(user_id)
        if not user_wallet:
            raise ValueError("User AA Wallet not found")
        
        amount_wei = self.w3.to_wei(amount_eth, 'ether')
        user_op = self._create_basic_user_op(user_wallet, nonce)
        user_op.update({"callData": "0x", "value": amount_wei, "to": self.ai_wallet_address})
        
        result = await self._sign_and_send_user_op_async(user_op, user_id, nonce)
        logger.info(f"Funded AI Wallet with {amount_eth} ETH from {user_id}: {result.get('result')}")
        return {"tx_hash": result.get("result", "pending"), "status": "success"}

    async def transfer_usdc_from_user(self, user_id: str, amount_usdc: int) -> Dict[str, str]:
        """Chuyển USDC từ ví user sang ví AI bất đồng bộ."""
        user_wallet, nonce = self.get_wallet(user_id)
        if not user_wallet:
            raise ValueError("User AA Wallet not found")
        
        user_op = self.create_user_op(user_wallet, "transfer", amount_usdc, nonce, self.ai_wallet_address)
        result = await self._sign_and_send_user_op_async(user_op, user_id, nonce)
        logger.info(f"Transferred {amount_usdc} USDC from {user_id} to AI Wallet: {result.get('result')}")
        return {"tx_hash": result.get("result", "pending"), "status": "success"}

    def _create_basic_user_op(self, wallet_address: str, nonce: int) -> Dict:
        """Tạo user operation cơ bản."""
        return {
            "sender": Web3.to_checksum_address(wallet_address),
            "nonce": nonce,
            "initCode": "0x",
            "callData": "0x",
            "callGasLimit": 200000,
            "verificationGasLimit": 100000,
            "preVerificationGas": 21000,
            "maxFeePerGas": self.w3.to_wei("2", 'gwei'),
            "maxPriorityFeePerGas": self.w3.to_wei('1', 'gwei'),
            "signature": "0x",
        }

    def create_user_op(self, wallet_address: str, action_type: str, amount: int, nonce: int, recipient: str = None) -> Dict:
        """Tạo user operation cho các hành động khác nhau."""
        wallet_contract = self.w3.eth.contract(address=wallet_address, abi=self.wallet_abi)
        
        if action_type == "swap":
            uniswap_contract = self.w3.eth.contract(address=self.uniswap_router, abi=self.uniswap_abi)
            swap_data = uniswap_contract.encodeABI(fn_name="exactInputSingle", args=[(
                self.usdc_address, self.weth_address, 3000, wallet_address, amount * 10**6, 0, 0
            )])
            call_data = wallet_contract.encodeABI(fn_name="execute", args=[self.uniswap_router, 0, swap_data])
        elif action_type == "supply":
            aave_contract = self.w3.eth.contract(address=self.aave_pool, abi=self.aave_abi)
            supply_data = aave_contract.encodeABI(fn_name="supply", args=[self.usdc_address, amount * 10**6, wallet_address, 0])
            call_data = wallet_contract.encodeABI(fn_name="execute", args=[self.aave_pool, 0, supply_data])
        elif action_type == "approve":
            usdc_contract = self.w3.eth.contract(address=self.usdc_address, abi=self.usdc_abi)
            approve_data = usdc_contract.encodeABI(fn_name="approve", args=[recipient or self.uniswap_router, amount * 10**6])
            call_data = wallet_contract.encodeABI(fn_name="execute", args=[self.usdc_address, 0, approve_data])
        elif action_type == "transfer":
            usdc_contract = self.w3.eth.contract(address=self.usdc_address, abi=self.usdc_abi)
            transfer_data = usdc_contract.encodeABI(fn_name="transfer", args=[recipient, amount * 10**6])
            call_data = wallet_contract.encodeABI(fn_name="execute", args=[self.usdc_address, 0, transfer_data])
        elif action_type == "withdraw":
            aave_contract = self.w3.eth.contract(address=self.aave_pool, abi=self.aave_abi)
            withdraw_data = aave_contract.encodeABI(fn_name="withdraw", args=[self.usdc_address, amount * 10**6, recipient])
            call_data = wallet_contract.encodeABI(fn_name="execute", args=[self.aave_pool, 0, withdraw_data])
        else:
            raise ValueError(f"Unsupported action_type: {action_type}")

        user_op = self._create_basic_user_op(wallet_address, nonce)
        user_op["callData"] = call_data
        return user_op

    async def _sign_and_send_user_op_async(self, user_op: Dict, user_id: str, nonce: int) -> Dict:
        """Ký và gửi user operation bất đồng bộ."""
        user_op_hash = self.w3.keccak(text=str(user_op))
        message = encode_defunct(hexstr=user_op_hash.hex())
        signature = self.kms_client.sign(
            KeyId=self.kms_key_id,
            Message=message.body,
            MessageType='DIGEST',
            SigningAlgorithm='ECDSA_SHA_256'
        )['Signature']
        user_op["signature"] = '0x' + signature.hex()

        async with aiohttp.ClientSession() as session:
            async with session.post(self.bundler_url, json={"jsonrpc": "2.0", "method": "eth_sendUserOperation", 
                                                            "params": [user_op, self.entry_point], "id": 1}) as response:
                result = await response.json()
                if "error" in result:
                    raise Exception(result["error"])
                self.update_nonce(user_id, nonce + 1)
                return result

    def update_nonce(self, user_id: str, new_nonce: int) -> None:
        """Cập nhật nonce trong database."""
        self.db.execute("UPDATE wallets SET nonce = ? WHERE user_id = ?", (new_nonce, user_id))

    async def swap_usdc_to_eth(self, amount_in: int, user_id: str) -> Dict[str, str]:
        """Swap USDC sang ETH trên Uniswap bất đồng bộ."""
        wallet_address, nonce = self.get_wallet(user_id)
        if not wallet_address:
            raise ValueError("AA wallet not found for user")
        
        approve_op = self.create_user_op(wallet_address, "approve", amount_in, nonce, self.uniswap_router)
        await self._sign_and_send_user_op_async(approve_op, user_id, nonce)

        nonce += 1
        user_op = self.create_user_op(wallet_address, "swap", amount_in, nonce)
        result = await self._sign_and_send_user_op_async(user_op, user_id, nonce)

        initial_value_usd = amount_in
        self.db.execute(
            "INSERT INTO positions (user_id, platform, initial_amount, initial_value_usd, start_time) VALUES (?, ?, ?, ?, ?)",
            (user_id, "uniswap", amount_in, initial_value_usd, int(time.time()))
        )
        return {"tx_hash": result.get("result", "pending")}

    async def supply_usdc(self, amount: int, user_id: str) -> Dict[str, str]:
        """Cung cấp USDC cho Aave bất đồng bộ."""
        wallet_address, nonce = self.get_wallet(user_id)
        if not wallet_address:
            raise ValueError("AA wallet not found for user")
        
        user_op = self.create_user_op(wallet_address, "supply", amount, nonce)
        result = await self._sign_and_send_user_op_async(user_op, user_id, nonce)

        initial_value_usd = amount
        self.db.execute(
            "INSERT INTO positions (user_id, platform, initial_amount, initial_value_usd, start_time) VALUES (?, ?, ?, ?, ?)",
            (user_id, "aave", amount, initial_value_usd, int(time.time()))
        )
        return {"tx_hash": result.get("result", "pending")}

    def get_aave_position_value(self, user_id: str, position_id: int) -> float:
        """Tính giá trị vị thế Aave."""
        position = self.db.fetch_one(
            "SELECT initial_amount FROM positions WHERE position_id = ? AND user_id = ? AND platform = 'aave'",
            (position_id, user_id)
        )
        if not position:
            raise ValueError("Position not found")
        initial_amount = position[0]

        apy = 0.05  # Giả định 5% APY
        current_time = int(time.time())
        start_time = self.db.fetch_one("SELECT start_time FROM positions WHERE position_id = ?", (position_id,))[0]
        time_elapsed_years = (current_time - start_time) / (365 * 24 * 3600)
        return initial_amount * (1 + apy * time_elapsed_years)

    def get_uniswap_position_value(self, user_id: str, position_id: int) -> float:
        """Tính giá trị vị thế Uniswap."""
        position = self.db.fetch_one(
            "SELECT initial_amount FROM positions WHERE position_id = ? AND user_id = ? AND platform = 'uniswap'",
            (position_id, user_id)
        )
        if not position:
            raise ValueError("Position not found")
        initial_amount = position[0]

        fee_earned = initial_amount * 0.003  # Giả định phí 0.3%
        return initial_amount + fee_earned

    async def check_and_withdraw(self, user_id: str) -> None:
        """Kiểm tra và rút vốn nếu đạt ngưỡng bất đồng bộ."""
        wallet_address, _ = self.get_wallet(user_id)
        if not wallet_address:
            raise ValueError("AA wallet not found for user")

        positions = self.db.fetch_all(
            "SELECT position_id, platform, initial_value_usd FROM positions WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        
        for position_id, platform, initial_value_usd in positions:
            current_value = (self.get_aave_position_value if platform == "aave" else self.get_uniswap_position_value)(user_id, position_id)
            profit_ratio = current_value / initial_value_usd
            
            if profit_ratio >= 1.05 or profit_ratio <= 0.99:
                nonce = self.get_wallet(user_id)[1]
                action_type = "withdraw" if platform == "aave" else "transfer"
                user_op = self.create_user_op(wallet_address, action_type, int(initial_value_usd), nonce, wallet_address)
                
                try:
                    result = await self._sign_and_send_user_op_async(user_op, user_id, nonce)
                    logger.info(f"Withdrawn {platform} position {position_id} for {user_id}. Profit ratio: {profit_ratio}")
                except Exception as e:
                    logger.error(f"Failed to withdraw {platform} position {position_id}: {str(e)}")
                    continue

    async def transfer_usdc(self, amount: int, user_id: str, recipient: str) -> Dict[str, str]:
        """Chuyển USDC từ ví user sang địa chỉ khác bất đồng bộ."""
        wallet_address, nonce = self.get_wallet(user_id)
        if not wallet_address:
            raise ValueError("AA wallet not found for user")
        
        user_op = self.create_user_op(wallet_address, "transfer", amount, nonce, recipient)
        result = await self._sign_and_send_user_op_async(user_op, user_id, nonce)
        return {"tx_hash": result.get("result", "pending")}

    async def withdraw_usdc(self, amount: int, user_id: str, recipient: str) -> Dict[str, str]:
        """Rút USDC từ Aave về ví khác bất đồng bộ."""
        wallet_address, nonce = self.get_wallet(user_id)
        if not wallet_address:
            raise ValueError("AA wallet not found for user")
        
        user_op = self.create_user_op(wallet_address, "withdraw", amount, nonce, recipient)
        result = await self._sign_and_send_user_op_async(user_op, user_id, nonce)
        return {"tx_hash": result.get("result", "pending")}