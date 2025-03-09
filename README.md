# AI-Powered DeFi Backend

This is a FastAPI-based backend that integrates AI querying (OpenAI, Anthropic, DeepSeek), Account Abstraction (AA) wallets for DeFi interactions (Uniswap, Aave), credit management for AI usage, and Stripe payments for purchasing credits. The system is designed to allow users to interact with DeFi protocols via natural language commands while managing gas fees and credits efficiently.

## Project Structure

```plaintext
backend/
├── ai_service.py        # Handles AI queries (OpenAI, Anthropic, DeepSeek)
├── defi_service.py      # Manages AA wallets and DeFi interactions (Aave, Uniswap)
├── credit_service.py    # Manages AI credits for users
├── database.py          # SQLite database for credits and wallets
├── stripe_service.py    # Stripe payment integration for buying credits
├── main.py             # FastAPI API layer
├── .env                # Configuration and API keys
├── wallets.db          # SQLite database for AA wallet storage
└── credits.db          # SQLite database for credit storage
```

## Features

- **AI Queries:** Process natural language commands using OpenAI, Anthropic, or DeepSeek models.
- **DeFi Interactions:** Execute DeFi actions (deposit, swap, transfer, withdraw) via AA wallets on Uniswap and Aave.
- **Credit System:** Manage AI usage credits; deduct credits per query and allow purchases.
- **Stripe Payments:** Purchase credits using Stripe.
- **Gas Funding:** Users fund the AI-Agent’s AA wallet with ETH to cover gas fees.

## Prerequisites

Before setting up the backend, ensure you have the following installed:

- **Python 3.8+**: Download from [python.org](https://www.python.org/).
- **pip**: Python package manager (comes with Python).
- **Git**: For cloning the repository (optional).

You’ll also need API keys and services:

- **Alchemy RPC URL** (for Ethereum blockchain access)
- **AWS KMS** (for signing UserOps)
- **Bundler URL** (for ERC-4337 AA wallet support)
- **API keys for OpenAI, Anthropic, DeepSeek**
- **Stripe API key**

## Setup Instructions

### 1. Clone the Repository (Optional)

If you’re using a Git repository:

```bash
git clone https://github.com/yourusername/your-repo.git
cd backend
```

Alternatively, create the folder structure manually and copy the provided files.

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install web3.py python-dotenv requests boto3 fastapi uvicorn stripe
```

### 3. Configure Environment Variables

Create a `.env` file in the `backend/` directory with the following content:

```plaintext
ALCHEMY_RPC_URL=https://your_alchemy_rpc_url
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
KMS_KEY_ID=your_kms_key_id
BUNDLER_URL=https://your_bundler_url
AI_AGENT_PRIVATE_KEY=your_ai_agent_private_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
STRIPE_API_KEY=your_stripe_api_key
```

Replace placeholders (e.g., `your_alchemy_rpc_url`) with your actual keys and URLs.

### 4. Initialize Databases

The backend uses SQLite databases (`wallets.db` and `credits.db`) which are created automatically when you run the application for the first time. No manual setup is needed.

### 5. Run the Backend

Start the FastAPI server:

```bash
cd backend
python main.py
```

The server will run on `http://0.0.0.0:8000`.

## Usage Guide

The backend exposes a single endpoint (`/api/v1/endpoint`) that handles all actions via `POST` requests. Below are examples of how to use each feature.

### API Endpoint

- **URL:** `POST /api/v1/endpoint`
- **Body:** JSON object with `action`, `user_id`, and additional parameters depending on the action.

#### 1. Check Credits

**Request:**

```json
{
    "action": "credits",
    "user_id": "user123"
}
```

**Response:**

```json
{"credits_remaining": 5}
```

#### 2. Create an AA Wallet

```json
{
    "action": "create_aa_wallet",
    "user_id": "user123"
}
```

**Response:** `{ "wallet_address": "0x..." }`

#### 3. Get AA Wallet Info

```json
{
    "action": "get_aa_wallet",
    "user_id": "user123"
}
```

**Response:** `{ "wallet_address": "0x...", "bytecode": "0x..." }`

#### 4. Fund AI Wallet with ETH

```json
{
    "action": "fund_ai_wallet",
    "user_id": "user123",
    "amount_eth": 0.01
}
```

**Response:** `{ "tx_hash": "0x...", "status": "success" }`

#### 5. Swap USDC to ETH

```json
{
    "action": "swap",
    "user_id": "user123",
    "amount_in": 50
}
```

**Response:** `{ "tx_hash": "0x...", "status": "success" }`

#### 6. Supply USDC to Aave

```json
{
    "action": "supply",
    "user_id": "user123",
    "amount": 50
}
```

**Response:** `{ "tx_hash": "0x...", "status": "success" }`

#### 7. Ask AI a Question

```json
{
    "action": "ask",
    "user_id": "user123",
    "question": "Ask DeepSeek deposit 50 USDC",
    "model": "deepseek"
}
```

**Response:** `{ "response": "Deposited 50 USDC to Uniswap pool. Tx hash: 0x..." }`

#### 8. Buy Credits with Stripe

```json
{
    "action": "buy_credits",
    "user_id": "user123",
    "amount": 10
}
```

**Response:** `{ "client_secret": "pi_xxx_secret_xxx", "payment_intent_id": "pi_xxx", "credits_to_add": 10 }`

#### 9. Confirm Credit Purchase

```json
{
    "action": "confirm_buy_credits",
    "user_id": "user123",
    "payment_intent_id": "pi_xxx",
    "credits_to_add": 10
}
```

**Response:** `{ "status": "success" }`

## Troubleshooting

- **Insufficient Credits:** Ensure you have enough credits (`credits` action) or buy more (`buy_credits`).
- **Gas Funding:** If DeFi actions fail, fund the AI wallet with ETH (`fund_ai_wallet`).
- **API Errors:** Check logs in the terminal for detailed error messages.

## Notes

- **Frontend Integration:** Use a frontend (e.g., React) to handle Stripe payments with `client_secret`.
- **Security:** Keep `.env` file secure and never commit it to version control.
- **Testing:** Test with small amounts (e.g., 0.001 ETH, 1 USDC) on a testnet first.

## Contributing

Feel free to submit issues or pull requests to improve this project!

