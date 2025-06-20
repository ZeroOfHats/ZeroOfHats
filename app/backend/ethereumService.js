const { ethers } = require('ethers');

// 1. Provider Setup (using a public testnet provider for now)
// Replace with your preferred provider: Infura, Alchemy, or a local node URI
const provider = ethers.getDefaultProvider('ropsten');
// For local development, you might use:
// const provider = new ethers.JsonRpcProvider('http://localhost:8545');

// 2. Signer Setup (Wallet)
// IMPORTANT: Never commit actual private keys. Use environment variables for real deployments.
// This is a DUMMY private key for demonstration purposes ONLY.
const DUMMY_PRIVATE_KEY = '0x0123456789012345678901234567890123456789012345678901234567890123'; // Replace with process.env.PRIVATE_KEY in a real app
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY || DUMMY_PRIVATE_KEY, provider);
console.log(`Using signer address: ${wallet.address}`);

// 3. Placeholder Contract Addresses
// Replace these with your actual deployed contract addresses
const PROPOSAL_CONTRACT_ADDRESS = process.env.PROPOSAL_CONTRACT_ADDRESS || '0xYourProposalContractAddress';
const NFT_CONTRACT_ADDRESS = process.env.NFT_CONTRACT_ADDRESS || '0xYourNFTContractAddress';

// 4. Simplified ABIs
const PROPOSAL_CONTRACT_ABI = [
    "function createProposal(string memory _description) public returns (uint)", // Assuming it returns proposalId (or we rely on event)
    "function castVote(uint256 _proposalId, uint8 _voteType) public", // Solidity enum often uint8
    "function proposals(uint256 id) view returns (uint256 id, string description, address proposer, uint256 yesVotes, uint256 noVotes, uint256 abstainVotes, uint256 discussionVotes, uint8 status)",
    "function nextProposalId() view returns (uint256)"
    // Add other function signatures from Proposal.sol if needed by the backend
];

const NFT_CONTRACT_ABI = [
    "function mint(address _to) public returns (uint256)", // Assuming it returns tokenId (or we rely on event)
    // Add other function signatures from InnovationNFT.sol if needed
];

// 5. Contract Instances
let proposalContract;
let nftContract;

try {
    if (PROPOSAL_CONTRACT_ADDRESS !== '0xYourProposalContractAddress' && ethers.isAddress(PROPOSAL_CONTRACT_ADDRESS)) {
        proposalContract = new ethers.Contract(PROPOSAL_CONTRACT_ADDRESS, PROPOSAL_CONTRACT_ABI, wallet);
    } else {
        console.warn("ProposalContract address is a placeholder or invalid. Contract instance not created.");
    }

    if (NFT_CONTRACT_ADDRESS !== '0xYourNFTContractAddress' && ethers.isAddress(NFT_CONTRACT_ADDRESS)) {
        nftContract = new ethers.Contract(NFT_CONTRACT_ADDRESS, NFT_CONTRACT_ABI, wallet);
    } else {
        console.warn("NFTContract address is a placeholder or invalid. Contract instance not created.");
    }
} catch (error) {
    console.error("Error creating contract instances:", error);
}


// --- Exportable Service Functions ---

/**
 * Creates a new proposal on the blockchain.
 * @param {string} description - The description of the proposal.
 * @returns {Promise<object>} An object containing the transaction hash and optionally the proposal ID.
 */
async function createNewProposal(description) {
    if (!proposalContract) {
        throw new Error('ProposalContract not initialized. Check address and ABI.');
    }
    try {
        // Estimate gas for the transaction
        const estimatedGas = await proposalContract.createProposal.estimateGas(description);
        console.log(`Estimated gas for createProposal: ${estimatedGas.toString()}`);

        const tx = await proposalContract.createProposal(description, {
            gasLimit: estimatedGas + BigInt(100000) // Add some buffer to gas limit
        });
        console.log(`Create proposal transaction sent: ${tx.hash}`);
        const receipt = await tx.wait();
        console.log(`Create proposal transaction confirmed. Block: ${receipt.blockNumber}`);

        // Assuming the contract emits an event like ProposalCreated(uint id, ...)
        // Or if createProposal returns the ID directly (modified ABI for that)
        // For now, we'll just return the hash. If ID is directly returned or easily parsed from receipt, that's better.
        // If the function returns the ID as specified in ABI: "returns (uint)"
        // const proposalId = receipt.events?.find(e => e.event === 'ProposalCreated')?.args?.id;
        // For direct return (if ABI is `returns (uint)` and contract does so):
        // The `tx` object itself might not directly contain return values for non-view functions.
        // We would typically get this from an event or if the function is changed to return it.
        // For simplicity, let's assume the ABI `returns (uint)` means we can get it from a call static first or from event

        // If createProposal returns the ID, we might need to call it statically first or parse from events
        // For now, let's assume the transaction hash is the primary outcome.
        // If the function `createProposal` in Solidity returns the ID, `tx.wait()` doesn't directly give it.
        // One way is to parse logs from `receipt.logs` if there's an event, or call it statically if it's simple.
        // The provided ABI "returns (uint)" suggests it might be directly returned.
        // However, for non-constant functions, the return value isn't directly in the transaction response.
        // It's usually obtained from events. Let's assume an event `ProposalCreated(uint id, ...)`
        // This part needs refinement based on actual contract event emission.

        return { transactionHash: tx.hash, receipt }; // proposalId: proposalId ? proposalId.toString() : null
    } catch (error) {
        console.error('Error creating proposal:', error);
        throw error;
    }
}

/**
 * Casts a vote on a proposal on the blockchain.
 * @param {number|string} proposalId - The ID of the proposal to vote on.
 * @param {number} voteType - The type of vote (0 for Yes, 1 for No, etc.).
 * @returns {Promise<object>} An object containing the transaction hash.
 */
async function castBlockchainVote(proposalId, voteType) {
    if (!proposalContract) {
        throw new Error('ProposalContract not initialized. Check address and ABI.');
    }
    try {
        const id = BigInt(proposalId); // Ensure proposalId is BigInt if it's uint256 in contract
        const type = Number(voteType); // Ensure voteType is a number

        const estimatedGas = await proposalContract.castVote.estimateGas(id, type);
        console.log(`Estimated gas for castVote: ${estimatedGas.toString()}`);

        const tx = await proposalContract.castVote(id, type, {
            gasLimit: estimatedGas + BigInt(100000)
        });
        console.log(`Cast vote transaction sent: ${tx.hash}`);
        const receipt = await tx.wait();
        console.log(`Cast vote transaction confirmed. Block: ${receipt.blockNumber}`);
        return { transactionHash: tx.hash, receipt };
    } catch (error) {
        console.error(`Error casting vote for proposal ${proposalId}:`, error);
        throw error;
    }
}

/**
 * Mints a new NFT to a specified address.
 * @param {string} recipientAddress - The address to mint the NFT to.
 * @returns {Promise<object>} An object containing the transaction hash and optionally the token ID.
 */
async function mintNFT(recipientAddress) {
    if (!nftContract) {
        throw new Error('NFTContract not initialized. Check address and ABI.');
    }
    if (!ethers.isAddress(recipientAddress)) {
        throw new Error('Invalid recipient address for minting NFT.');
    }
    try {
        const estimatedGas = await nftContract.mint.estimateGas(recipientAddress);
        console.log(`Estimated gas for mint: ${estimatedGas.toString()}`);

        const tx = await nftContract.mint(recipientAddress, {
            gasLimit: estimatedGas + BigInt(100000)
        });
        console.log(`Mint NFT transaction sent: ${tx.hash}`);
        const receipt = await tx.wait();
        console.log(`Mint NFT transaction confirmed. Block: ${receipt.blockNumber}`);
        // Similar to createProposal, getting tokenId might require parsing events (e.g., Transfer event)
        // For simplicity, returning hash.
        // const tokenId = receipt.events?.find(e => e.event === 'Transfer' && e.args.from === ethers.ZeroAddress)?.args?.tokenId;
        return { transactionHash: tx.hash, receipt }; // tokenId: tokenId ? tokenId.toString() : null
    } catch (error) {
        console.error(`Error minting NFT to ${recipientAddress}:`, error);
        throw error;
    }
}

module.exports = {
    createNewProposal,
    castBlockchainVote,
    mintNFT,
    getProposalDetails,
    listProposals,
    // Expose provider, wallet, or contracts if needed directly by other parts of the app, but usually it's better to wrap.
};

// Helper to parse proposal struct from contract call result
function _parseProposalData(proposalArray) {
    // Order must match the return values of the `proposals` function in the ABI
    return {
        id: proposalArray[0].toString(), // Convert BigInt to string for JSON compatibility
        description: proposalArray[1],
        proposer: proposalArray[2],
        yesVotes: proposalArray[3].toString(),
        noVotes: proposalArray[4].toString(),
        abstainVotes: proposalArray[5].toString(),
        discussionVotes: proposalArray[6].toString(),
        status: proposalArray[7] // Enum will be a number (0 for Pending, 1 for Approved, etc.)
        // Consider mapping status number to string e.g. ProposalStatus[proposalArray[7]]
    };
}


/**
 * Fetches details for a specific proposal from the blockchain.
 * @param {string|number} proposalId - The ID of the proposal.
 * @returns {Promise<object|null>} The proposal details or null if not found.
 */
async function getProposalDetails(proposalId) {
    if (!proposalContract) {
        throw new Error('ProposalContract not initialized.');
    }
    try {
        const id = BigInt(proposalId);
        const proposalData = await proposalContract.proposals(id);
        // Check if proposal exists (e.g., if proposer is not address(0) or id is not 0)
        if (proposalData.proposer === ethers.ZeroAddress && proposalData.id === BigInt(0)) {
            return null; // Or throw an error: throw new Error(`Proposal with ID ${proposalId} not found.`);
        }
        return _parseProposalData(proposalData);
    } catch (error) {
        console.error(`Error fetching details for proposal ${proposalId}:`, error);
        // It's common for contracts to revert if an ID doesn't exist.
        if (error.message.includes('reverted') || error.message.includes('invalid BigNumber value')) {
            return null; // Treat revert as "not found"
        }
        throw error;
    }
}

/**
 * Fetches a list of all proposals from the blockchain.
 * @returns {Promise<Array<object>>} A list of proposal objects.
 */
async function listProposals() {
    if (!proposalContract) {
        throw new Error('ProposalContract not initialized.');
    }
    try {
        const maxId = await proposalContract.nextProposalId(); // This is the *next* ID to be used
        const proposalsList = [];
        // Assuming proposal IDs start from 1 and go up to maxId - 1
        for (let i = BigInt(1); i < maxId; i++) {
            try {
                const proposalData = await proposalContract.proposals(i);
                 // Basic check if proposal is valid (e.g., proposer is not zero address)
                if (proposalData.proposer !== ethers.ZeroAddress && proposalData.id !== BigInt(0)) {
                    proposalsList.push(_parseProposalData(proposalData));
                }
            } catch (err) {
                // If a specific ID is missing or causes error, log it and continue
                console.warn(`Could not fetch proposal with ID ${i}: ${err.message}. Skipping.`);
            }
        }
        return proposalsList;
    } catch (error) {
        console.error('Error listing proposals:', error);
        throw error;
    }
}
