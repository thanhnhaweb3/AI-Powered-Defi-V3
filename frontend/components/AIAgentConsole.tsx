import { useState, useEffect } from "react";
import { useAccount, useBalance, useReadContract } from "wagmi";
import axios from "axios";
import { Elements, CardElement, useStripe, useElements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { Address } from "~~/components/scaffold-eth";
import { notification } from "~~/utils/scaffold-eth";
import { ERC20_ABI } from "~~/components/abis/ERC20";
import { ethers } from "ethers";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000/ai_credit_endpoint";
const USDC_ADDRESS = process.env.NEXT_PUBLIC_USDC_ADDRESS || "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // Base USDC
const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "pk_test_your_key";
const stripePromise = loadStripe(STRIPE_PUBLISHABLE_KEY);

const CheckoutForm = ({ 
  amount, 
  address, 
  onSuccess, 
  onError, 
  setLoading 
}: { 
  amount: number, 
  address: string, 
  onSuccess: () => void, 
  onError: (error: string) => void,
  setLoading: (loading: boolean) => void 
}) => {
  const stripe = useStripe();
  const elements = useElements();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setLoading(true);

    try {
      const response = await axios.post(BACKEND_URL, { 
        user_id: address, 
        amount,
        action: "buy_credits"
      });
      const { client_secret, payment_intent_id, credits_to_add } = response.data;

      const cardElement = elements.getElement(CardElement);
      if (!cardElement) throw new Error("Card element not found");

      const result = await stripe.confirmCardPayment(client_secret, {
        payment_method: { card: cardElement },
      });

      if (result.error) throw new Error(result.error.message);

      await axios.post(BACKEND_URL, {
        user_id: address,
        payment_intent_id,
        credits_to_add,
        action: "confirm_buy_credits"
      });

      onSuccess();
      notification.success(`Bought ${amount} credits successfully!`);
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || "Payment failed";
      onError(errorMsg);
      notification.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-control mb-4">
        <label className="label">
          <span className="label-text">Card Details</span>
        </label>
        <CardElement className="input input-bordered p-2" options={{
          style: {
            base: { fontSize: "16px", color: "#424770", "::placeholder": { color: "#aab7c4" } },
            invalid: { color: "#9e2146" },
          },
        }} />
      </div>
      <div className="modal-action">
        <button type="submit" className="btn btn-primary" disabled={!stripe}>
          Submit Payment
        </button>
      </div>
    </form>
  );
};

export const AIAgentConsole = () => {
  const { address } = useAccount();
  const [credits, setCredits] = useState<number>(0);
  const [command, setCommand] = useState<string>("");
  const [output, setOutput] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [buyAmount, setBuyAmount] = useState<string>("");
  const [showPaymentForm, setShowPaymentForm] = useState<boolean>(false);
  const [aaWalletAddress, setAaWalletAddress] = useState<string | null>(null);
  const [aaWalletBytecode, setAaWalletBytecode] = useState<string | null>(null);
  const [aaWalletStatus, setAaWalletStatus] = useState<"loading" | "exists" | "not_exists">("loading");
  const [fundAmount, setFundAmount] = useState<string>("");
  const [transferAmount, setTransferAmount] = useState<string>("");
  const [withdrawAmount, setWithdrawAmount] = useState<string>("");

  const { data: ethBalance } = useBalance({ address, chainId: 8453 }); // Base Mainnet
  const { data: aaEthBalance } = useBalance({ address: aaWalletAddress as `0x${string}`, chainId: 8453 });
  const { data: usdcBalance } = useReadContract({
    address: USDC_ADDRESS as `0x${string}`,
    abi: ERC20_ABI,
    functionName: "balanceOf",
    args: [aaWalletAddress || address],
  });
  const { data: usdcDecimals } = useReadContract({
    address: USDC_ADDRESS as `0x${string}`,
    abi: ERC20_ABI,
    functionName: "decimals",
  });

  useEffect(() => {
    if (address) {
      setAaWalletStatus("loading");
      checkAAWallet();
      fetchCredits();
    } else {
      resetState();
    }
  }, [address]);

  const resetState = () => {
    setAaWalletAddress(null);
    setAaWalletBytecode(null);
    setAaWalletStatus("not_exists");
    setCredits(0);
    setOutput([]);
    setCommand("");
    setBuyAmount("");
    setFundAmount("");
    setTransferAmount("");
    setWithdrawAmount("");
  };

  const fetchCredits = async () => {
    if (!address) return;
    try {
      const response = await axios.post(BACKEND_URL, { user_id: address, action: "credits" });
      setCredits(response.data.credits_remaining);
    } catch (error: any) {
      handleError(error, "Failed to fetch credits");
    }
  };

  const checkAAWallet = async () => {
    if (!address) return;
    try {
      const response = await axios.post(BACKEND_URL, { user_id: address, action: "get_aa_wallet" });
      const { wallet_address, bytecode } = response.data;
      setAaWalletAddress(wallet_address || null);
      setAaWalletBytecode(bytecode || null);
      setAaWalletStatus(wallet_address ? "exists" : "not_exists");
    } catch (error: any) {
      handleError(error, "Failed to check AA wallet");
      setAaWalletStatus("not_exists");
    }
  };

  const deployAAWallet = async () => {
    if (!address) return;
    setLoading(true);
    try {
      const response = await axios.post(BACKEND_URL, { user_id: address, action: "create_aa_wallet" });
      const { wallet_address, bytecode } = response.data;
      setAaWalletAddress(wallet_address);
      setAaWalletBytecode(bytecode);
      setAaWalletStatus("exists");
      setOutput([...output, `AA Wallet created at: ${wallet_address}`, `Bytecode: ${bytecode.slice(0, 50)}...`]);
      notification.success("AA Wallet created successfully!");
    } catch (error: any) {
      handleError(error, "Failed to create AA wallet");
    } finally {
      setLoading(false);
    }
  };

  const handleCommand = async () => {
    if (!command || !address || !aaWalletAddress) return;
    setLoading(true);
    const parts = command.trim().toLowerCase().split(" ");
    const action = parts[0];
    setOutput([...output, `> ${command}`]);

    try {
      switch (action) {
        case "ask": {
          const model = parts[1] || "anthropic";
          const question = parts.slice(2).join(" ");
          const response = await axios.post(BACKEND_URL, { 
            user_id: address, 
            question, 
            model,
            action: "ask"
          });
          setOutput([...output, `> ${command}`, response.data.response]);
          fetchCredits();
          break;
        }
        case "swap":
        case "supply": {
          const amount = parseFloat(parts[1]);
          if (isNaN(amount)) throw new Error("Invalid amount");
          const response = await axios.post(BACKEND_URL, { 
            user_id: address, 
            [action === "swap" ? "amount_in" : "amount"]: amount,
            action
          });
          setOutput([...output, `> ${command}`, `${action} Tx Hash: ${response.data.tx_hash}`]);
          break;
        }
        case "fund": {
          const amount = parseFloat(parts[1]);
          if (isNaN(amount)) throw new Error("Invalid amount");
          const response = await axios.post(BACKEND_URL, { 
            user_id: address, 
            amount_eth: amount,
            action: "fund_ai_wallet"
          });
          setOutput([...output, `> ${command}`, `Funded AI Wallet Tx Hash: ${response.data.tx_hash}`]);
          break;
        }
        case "transfer": {
          const amount = parseFloat(parts[1]);
          const recipient = parts[2];
          if (isNaN(amount) || !ethers.isAddress(recipient)) throw new Error("Invalid amount or recipient");
          const response = await axios.post(BACKEND_URL, { 
            user_id: address, 
            amount,
            recipient,
            action: "transfer_usdc"
          });
          setOutput([...output, `> ${command}`, `Transfer USDC Tx Hash: ${response.data.tx_hash}`]);
          break;
        }
        case "withdraw": {
          const amount = parseFloat(parts[1]);
          const recipient = parts[2];
          if (isNaN(amount) || !ethers.isAddress(recipient)) throw new Error("Invalid amount or recipient");
          const response = await axios.post(BACKEND_URL, { 
            user_id: address, 
            amount,
            recipient,
            action: "withdraw_usdc"
          });
          setOutput([...output, `> ${command}`, `Withdraw USDC Tx Hash: ${response.data.tx_hash}`]);
          break;
        }
        case "check_profits": {
          const response = await axios.post(BACKEND_URL, { 
            user_id: address, 
            action: "check_profits"
          });
          if (response.data.status === "no_active_positions") {
            setOutput([...output, `> ${command}`, "No active positions found."]);
          } else {
            const positions = response.data.positions.map((pos: any) => 
              `Position ${pos.position_id} (${pos.platform}): Initial: ${pos.initial_value_usd} USD, Current: ${pos.current_value_usd.toFixed(2)} USD, Profit: ${(pos.profit_ratio * 100 - 100).toFixed(2)}%, Action: ${pos.action_taken || "None"}`
            );
            setOutput([...output, `> ${command}`, ...positions]);
          }
          break;
        }
        default:
          setOutput([...output, `> ${command}`, "Invalid command. Use: ask <model> <question>, swap <amount>, supply <amount>, fund <amount>, transfer <amount> <recipient>, withdraw <amount> <recipient>, check_profits"]);
      }
    } catch (error: any) {
      handleError(error, "Command execution failed");
    } finally {
      setCommand("");
      setLoading(false);
    }
  };

  const handleBuySuccess = () => {
    fetchCredits();
    setBuyAmount("");
    setShowPaymentForm(false);
    setOutput([...output, `Bought ${buyAmount} credits successfully!`]);
  };

  const handleFundAIWallet = async () => {
    if (!fundAmount || !address || !aaWalletAddress) return;
    setLoading(true);
    try {
      const amount = parseFloat(fundAmount);
      if (isNaN(amount)) throw new Error("Invalid amount");
      const response = await axios.post(BACKEND_URL, { 
        user_id: address, 
        amount_eth: amount,
        action: "fund_ai_wallet"
      });
      setOutput([...output, `Funded AI Wallet with ${amount} ETH - Tx Hash: ${response.data.tx_hash}`]);
      notification.success(`Funded AI Wallet with ${amount} ETH!`);
    } catch (error: any) {
      handleError(error, "Failed to fund AI Wallet");
    } finally {
      setFundAmount("");
      setLoading(false);
    }
  };

  const handleTransferUSDC = async () => {
    if (!transferAmount || !address || !aaWalletAddress) return;
    setLoading(true);
    try {
      const amount = parseFloat(transferAmount);
      const recipient = prompt("Enter recipient address:");
      if (isNaN(amount) || !recipient || !ethers.isAddress(recipient)) throw new Error("Invalid amount or recipient");
      const response = await axios.post(BACKEND_URL, { 
        user_id: address, 
        amount,
        recipient,
        action: "transfer_usdc"
      });
      setOutput([...output, `Transferred ${amount} USDC to ${recipient} - Tx Hash: ${response.data.tx_hash}`]);
      notification.success(`Transferred ${amount} USDC!`);
    } catch (error: any) {
      handleError(error, "Failed to transfer USDC");
    } finally {
      setTransferAmount("");
      setLoading(false);
    }
  };

  const handleWithdrawUSDC = async () => {
    if (!withdrawAmount || !address || !aaWalletAddress) return;
    setLoading(true);
    try {
      const amount = parseFloat(withdrawAmount);
      const recipient = prompt("Enter recipient address:");
      if (isNaN(amount) || !recipient || !ethers.isAddress(recipient)) throw new Error("Invalid amount or recipient");
      const response = await axios.post(BACKEND_URL, { 
        user_id: address, 
        amount,
        recipient,
        action: "withdraw_usdc"
      });
      setOutput([...output, `Withdrawn ${amount} USDC to ${recipient} - Tx Hash: ${response.data.tx_hash}`]);
      notification.success(`Withdrawn ${amount} USDC!`);
    } catch (error: any) {
      handleError(error, "Failed to withdraw USDC");
    } finally {
      setWithdrawAmount("");
      setLoading(false);
    }
  };

  const handleError = (error: any, defaultMsg: string) => {
    const errorMsg = error.response?.data?.detail || error.message || defaultMsg;
    console.error(errorMsg);
    notification.error(errorMsg);
    setOutput([...output, `Error: ${errorMsg}`]);
  };

  const formattedUsdcBalance = usdcBalance && usdcDecimals 
    ? (Number(usdcBalance) / 10 ** Number(usdcDecimals)).toFixed(2) 
    : "0";

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="card bg-base-100 shadow-xl mb-6">
        <div className="card-body">
          {address ? (
            <>
              <p>Connected Address: <Address address={address} /></p>
              <p>ETH Balance: {ethBalance?.formatted || "0"} ETH</p>
              {aaWalletAddress ? (
                <>
                  <p>AA Wallet: <Address address={aaWalletAddress} /></p>
                  <p className="font-mono text-sm break-all">
                    Bytecode: {aaWalletBytecode ? `${aaWalletBytecode.slice(0, 50)}...` : "Loading..."}
                  </p>
                  <p>AA Wallet ETH Balance: {aaEthBalance?.formatted || "0"} ETH</p>
                  <p>AA Wallet USDC Balance: {formattedUsdcBalance} USDC</p>
                </>
              ) : (
                <p>AA Wallet: {aaWalletStatus === "loading" ? "Checking..." : "Not created"}</p>
              )}
              <p>AI Credits: {credits}</p>
              {aaWalletStatus === "not_exists" && (
                <button
                  onClick={deployAAWallet}
                  className="btn btn-primary mt-2"
                  disabled={loading}
                >
                  {loading ? "Creating..." : "Create AA Wallet"}
                </button>
              )}
            </>
          ) : (
            <p className="text-error">Please connect your wallet!</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h3 className="font-bold">Buy Credits</h3>
            <div className="flex gap-2">
              <input
                type="number"
                value={buyAmount}
                onChange={(e) => setBuyAmount(e.target.value)}
                placeholder="Amount of credits"
                className="input input-bordered w-40"
                disabled={!address || loading}
              />
              <button
                onClick={() => setShowPaymentForm(true)}
                className="btn btn-success"
                disabled={!address || !buyAmount || loading}
              >
                {loading ? "Processing..." : "Buy"}
              </button>
            </div>
            {showPaymentForm && (
              <div className="modal modal-open">
                <div className="modal-box">
                  <h3 className="font-bold text-lg">Payment Details</h3>
                  <Elements stripe={stripePromise}>
                    <CheckoutForm 
                      amount={parseInt(buyAmount)} 
                      address={address!} 
                      onSuccess={handleBuySuccess} 
                      onError={handleError}
                      setLoading={setLoading}
                    />
                  </Elements>
                  <div className="modal-action">
                    <button
                      type="button"
                      className="btn"
                      onClick={() => setShowPaymentForm(false)}
                      disabled={loading}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h3 className="font-bold">Fund AI Wallet</h3>
            <div className="flex gap-2">
              <input
                type="number"
                value={fundAmount}
                onChange={(e) => setFundAmount(e.target.value)}
                placeholder="ETH amount"
                className="input input-bordered w-40"
                disabled={!address || !aaWalletAddress || loading}
              />
              <button
                onClick={handleFundAIWallet}
                className="btn btn-accent"
                disabled={!address || !fundAmount || !aaWalletAddress || loading}
              >
                {loading ? "Funding..." : "Fund"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h3 className="font-bold">Transfer USDC</h3>
            <div className="flex gap-2">
              <input
                type="number"
                value={transferAmount}
                onChange={(e) => setTransferAmount(e.target.value)}
                placeholder="USDC amount"
                className="input input-bordered w-40"
                disabled={!address || !aaWalletAddress || loading}
              />
              <button
                onClick={handleTransferUSDC}
                className="btn btn-warning"
                disabled={!address || !transferAmount || !aaWalletAddress || loading}
              >
                {loading ? "Transferring..." : "Transfer"}
              </button>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h3 className="font-bold">Withdraw USDC</h3>
            <div className="flex gap-2">
              <input
                type="number"
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
                placeholder="USDC amount"
                className="input input-bordered w-40"
                disabled={!address || !aaWalletAddress || loading}
              />
              <button
                onClick={handleWithdrawUSDC}
                className="btn btn-error"
                disabled={!address || !withdrawAmount || !aaWalletAddress || loading}
              >
                {loading ? "Withdrawing..." : "Withdraw"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card bg-base-100 shadow-xl">
        <div className="card-body">
          <h3 className="font-bold">AI Agent Console</h3>
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleCommand()}
            placeholder="e.g., ask anthropic What is DeFi?, swap 10, supply 20, fund 0.1, transfer 10 0x..., withdraw 10 0x..., check_profits"
            className="input input-bordered w-full"
            disabled={!address || !aaWalletAddress || loading}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleCommand}
              className="btn btn-primary"
              disabled={!address || !command || !aaWalletAddress || loading}
            >
              {loading ? "Executing..." : "Run"}
            </button>
            <button
              onClick={() => handleCommand({ target: { value: "check_profits" } } as any)}
              className="btn btn-info"
              disabled={!address || !aaWalletAddress || loading}
            >
              Check Profits
            </button>
          </div>

          <div className="bg-base-200 p-4 rounded-lg h-64 overflow-y-auto mt-4 font-mono text-sm">
            {output.map((line, index) => (
              <p key={index}>{line}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
