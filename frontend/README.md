# AI Agent Client

This is a decentralized application (dApp) built using the Scaffold-ETH 2 framework. The AI Agent Client integrates with a backend powered by FastAPI and DeFi services, enabling users to interact with an AI-powered console, manage an Account Abstraction (AA) wallet, and perform DeFi operations like swapping, supplying, transferring, and withdrawing USDC on the Base Mainnet.

This README guides you through the setup process and provides detailed instructions on how to use the `AIAgentConsole.tsx` component.

## Prerequisites

Before you begin, ensure you have the following installed:

- Git
- Node.js (v18 or higher)
- Yarn (recommended package manager)
- A wallet extension like MetaMask
- A backend server running the AI Agent services (refer to the backend documentation for setup)

## Installation

Follow these steps to set up the AI Agent Client:

### 1. Clone the Repository

Clone the scaffold-eth-2 repository and name your project `my-ai-agent`:

```bash
git clone https://github.com/scaffold-eth/scaffold-eth-2.git my-ai-agent
cd my-ai-agent
```

### 2. Install Dependencies

Install the required dependencies using Yarn:

```bash
yarn install
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory and add the following environment variables:

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000/api/v1/endpoint
NEXT_PUBLIC_USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
```

- `NEXT_PUBLIC_BACKEND_URL`: The URL of your FastAPI backend (update if your backend runs on a different host/port).
- `NEXT_PUBLIC_USDC_ADDRESS`: The USDC contract address on Base Mainnet (default provided).
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key for credit purchases (replace with your actual key).

### 4. Replace `AIAgentConsole.tsx`

Replace the default `AIAgentConsole.tsx` file in `packages/nextjs/components/` with the provided code:

- Navigate to `packages/nextjs/components/`.
- Create or overwrite `AIAgentConsole.tsx` with the code provided in this repository.

### 5. Update Routing (Optional)

To use `AIAgentConsole.tsx` as the main component:

Open `packages/nextjs/pages/index.tsx` and replace its content with:

```tsx
import { AIAgentConsole } from "../components/AIAgentConsole";

export default function Home() {
  return <AIAgentConsole />;
}
```

### 6. Run the Application

Start the development server:

```bash
yarn dev
```

Open your browser and navigate to [http://localhost:3000](http://localhost:3000).

Ensure your MetaMask wallet is connected to the Base Mainnet (`chainId: 8453`).

## Using `AIAgentConsole.tsx`

The `AIAgentConsole.tsx` component provides a user interface to interact with the AI Agent and DeFi services. Below is a detailed guide on its features and usage.

### Overview

- **Purpose**: Allows users to connect their wallet, manage an AA wallet, buy AI credits, execute DeFi commands, and monitor profits.
- **Network**: Operates on Base Mainnet (`chainId: 8453`).
- **Dependencies**: Uses Wagmi for wallet interactions, Axios for API calls, and Stripe for payments.

### Features

#### Wallet Connection
- Connect your MetaMask wallet to see your address, ETH balance, and AA wallet details (if created).
- If no AA wallet exists, click "Create AA Wallet" to deploy one.

#### Buy Credits
- Input the number of credits to buy and click "Buy".
- A modal will appear for Stripe payment entry (card details).
- Credits are used for AI queries (`ask` command).

#### Fund AI Wallet
- Input an ETH amount and click "Fund" to send ETH to the AI wallet for gas fees.

#### Transfer USDC
- Input a USDC amount and click "Transfer". Enter the recipient address in the prompt.
- Transfers USDC from your AA wallet to another address.

#### Withdraw USDC
- Input a USDC amount and click "Withdraw". Enter the recipient address in the prompt.
- Withdraws USDC from Aave to the specified address.

#### AI Agent Console
- Use the command input to execute various actions (see **Commands** section).
- Output is displayed in a scrollable log below the input.

#### Check Profits
- Click "Check Profits" or use the `check_profits` command to view active positions and their profitability.

### Commands

Enter these commands in the console input and press "Run" or hit Enter:

- **`ask <model> <question>`**: Queries the AI with a specified model (e.g., Anthropics).
  - Example: `ask anthropic What is DeFi?`
  - Cost: 1 credit per query.

- **`swap <amount>`**: Swaps `<amount>` USDC to ETH on Uniswap.
  - Example: `swap 10`

- **`supply <amount>`**: Supplies `<amount>` USDC to Aave.
  - Example: `supply 20`

- **`fund <amount>`**: Funds the AI wallet with `<amount>` ETH.
  - Example: `fund 0.1`

- **`transfer <amount> <recipient>`**: Transfers `<amount>` USDC to `<recipient>` address.
  - Example: `transfer 10 0x1234...`

- **`withdraw <amount> <recipient>`**: Withdraws `<amount>` USDC from Aave to `<recipient>` address.
  - Example: `withdraw 10 0x1234...`

- **`check_profits`**: Displays active positions, their current value, profit percentage, and any actions taken (e.g., auto-withdrawal).
  - Example: `check_profits`

### UI Breakdown

- **Top Card**: Displays wallet info (address, ETH balance, AA wallet details, credits).
- **Buy Credits Section**: Input and button to purchase credits via Stripe.
- **Fund AI Wallet Section**: Input and button to send ETH to the AI wallet.
- **Transfer USDC Section**: Input and button to transfer USDC.
- **Withdraw USDC Section**: Input and button to withdraw USDC from Aave.
- **Console Section**: Command input, "Run" button, "Check Profits" button, and output log.

## Error Handling

- **"Network Error"**: Ensure the backend is running at `http://localhost:8000/api/v1/endpoint` and update `NEXT_PUBLIC_BACKEND_URL` if needed.
- **AA Wallet Not Created**: Check backend logs for deployment issues (e.g., insufficient gas).
- **Stripe Payment Fails**: Verify your `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` is correct and the backend Stripe integration is set up.

## Contributing

Feel free to fork this repository, make improvements, and submit pull requests to enhance the AI Agent Client.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

