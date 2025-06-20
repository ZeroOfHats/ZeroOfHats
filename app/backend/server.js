const express = require('express');
const path = require('path'); // Added path module
const {
    createNewProposal,
    castBlockchainVote,
    mintNFT,
    getProposalDetails,
    listProposals
} = require('./ethereumService'); // Import ethers functions

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware to parse JSON bodies
app.use(express.json());

// Placeholder for "Inform" Post Endpoint
app.post('/api/inform', (req, res) => {
    const { topic, knowledge } = req.body;
    console.log('Received "inform" data:');
    console.log('Topic:', topic);
    console.log('Knowledge:', knowledge);
    // In a real application, you would store this data in a database
    // and potentially interact with the blockchain (e.g., mint an NFT).
    res.status(200).json({ message: 'Inform data received', topic, knowledge });
});

// Placeholder for User Registration Endpoint
app.post('/api/users/register', (req, res) => {
    const { username, ethereumAddress } = req.body;
    console.log('Received user registration data:');
    console.log('Username:', username);
    console.log('Ethereum Address:', ethereumAddress);
    // In a real application, you would store this user data in a database.
    res.status(201).json({ message: 'User registered successfully', username, ethereumAddress });
});

// --- Discussion Endpoints ---

// Create Discussion Thread Endpoint (Placeholder)
// Linked to an "inform" post
app.post('/api/inform/:informPostId/discussions', (req, res) => {
    const { informPostId } = req.params;
    const { title, initialComment, userId } = req.body; // Assuming userId might be sent, or derived from auth later
    console.log(`Received request to create discussion for informPostId: ${informPostId}`);
    console.log('Title:', title);
    console.log('Initial Comment:', initialComment);
    console.log('User ID:', userId);
    // In a real app, create a discussion record linked to informPostId and userId
    res.status(201).json({
        message: 'Discussion thread created successfully (placeholder)',
        informPostId,
        discussionId: `disc${Date.now()}`, // Placeholder ID
        title,
        initialComment
    });
});

// Add Comment to Discussion Endpoint (Placeholder)
app.post('/api/discussions/:discussionId/comments', (req, res) => {
    const { discussionId } = req.params;
    const { userId, commentText } = req.body; // userId from auth in real app
    console.log(`Received comment for discussionId: ${discussionId}`);
    console.log('User ID:', userId);
    console.log('Comment Text:', commentText);
    // In a real app, add comment to the specified discussion, linking to userId
    res.status(201).json({
        message: 'Comment added successfully (placeholder)',
        discussionId,
        commentId: `comm${Date.now()}`, // Placeholder ID
        commentText
    });
});

// List Discussions Endpoint (Placeholder)
// For a specific "inform" post
app.get('/api/inform/:informPostId/discussions', (req, res) => {
    const { informPostId } = req.params;
    console.log(`Request to list discussions for informPostId: ${informPostId}`);
    // In a real app, fetch discussions from DB for informPostId
    const placeholderDiscussions = [
        { id: 'disc001', informPostId, title: 'Discussion about XYZ', commentCount: 2, createdAt: new Date().toISOString() },
        { id: 'disc002', informPostId, title: 'Another take on XYZ', commentCount: 5, createdAt: new Date().toISOString() }
    ];
    res.status(200).json(placeholderDiscussions);
});

// List Comments Endpoint (Placeholder)
// For a specific discussion
app.get('/api/discussions/:discussionId/comments', (req, res) => {
    const { discussionId } = req.params;
    console.log(`Request to list comments for discussionId: ${discussionId}`);
    // In a real app, fetch comments from DB for discussionId
    const placeholderComments = [
        { id: 'comm001', discussionId, userId: 'user123', text: 'Great point!', createdAt: new Date().toISOString() },
        { id: 'comm002', discussionId, userId: 'user456', text: 'I disagree, because...', createdAt: new Date().toISOString() }
    ];
    res.status(200).json(placeholderComments);
});

// --- Blockchain Interaction Endpoints ---

// Create Proposal Endpoint
app.post('/api/proposals', async (req, res) => {
    const { description } = req.body;
    if (!description) {
        return res.status(400).json({ error: 'Description is required' });
    }

    try {
        const result = await createNewProposal(description);
        // The result currently contains { transactionHash, receipt }
        // We might want to parse proposalId from receipt.logs if an event is emitted.
        console.log('Proposal creation result:', result);
        res.status(201).json({
            message: 'Proposal creation transaction sent',
            transactionHash: result.transactionHash,
            blockNumber: result.receipt.blockNumber
            // proposalId: result.proposalId // If available
        });
    } catch (error)
 {
        console.error('Failed to create proposal:', error.message);
        res.status(500).json({ error: 'Failed to send proposal transaction', details: error.message });
    }
});

// Mint NFT Endpoint
app.post('/api/nfts/mint', async (req, res) => {
    const { recipientAddress } = req.body;
    if (!recipientAddress || !require('ethers').isAddress(recipientAddress)) {
        return res.status(400).json({ error: 'Valid recipientAddress is required' });
    }

    try {
        const result = await mintNFT(recipientAddress);
        console.log('NFT Minting result:', result);
        res.status(201).json({
            message: 'NFT minting transaction sent',
            transactionHash: result.transactionHash,
            blockNumber: result.receipt.blockNumber
            // tokenId: result.tokenId // If available from ethereumService
        });
    } catch (error) {
        console.error('Failed to mint NFT:', error.message);
        res.status(500).json({ error: 'Failed to send NFT minting transaction', details: error.message });
    }
});

// Get Proposal Details Endpoint
app.get('/api/proposals/:proposalId', async (req, res) => {
    const { proposalId } = req.params;
    if (!proposalId) {
        return res.status(400).json({ error: 'Proposal ID is required' });
    }

    try {
        const proposal = await getProposalDetails(proposalId);
        if (proposal) {
            res.status(200).json(proposal);
        } else {
            res.status(404).json({ error: `Proposal with ID ${proposalId} not found` });
        }
    } catch (error) {
        console.error(`Failed to fetch proposal ${proposalId}:`, error.message);
        res.status(500).json({ error: 'Failed to fetch proposal details', details: error.message });
    }
});

// List All Proposals Endpoint
app.get('/api/proposals', async (req, res) => {
    try {
        const proposals = await listProposals();
        res.status(200).json(proposals);
    } catch (error) {
        console.error('Failed to list proposals:', error.message);
        res.status(500).json({ error: 'Failed to list proposals', details: error.message });
    }
});

// Cast Vote Endpoint
app.post('/api/proposals/:proposalId/vote', async (req, res) => {
    const { proposalId } = req.params;
    const { voteType } = req.body; // voteType: 0 for Yes, 1 for No, etc.

    if (voteType === undefined || typeof voteType !== 'number') {
        return res.status(400).json({ error: 'Valid voteType (number) is required' });
    }
    if (!proposalId) {
        return res.status(400).json({ error: 'Proposal ID is required' });
    }

    try {
        const result = await castBlockchainVote(proposalId, voteType);
        console.log('Vote casting result:', result);
        res.status(200).json({
            message: 'Vote transaction sent',
            transactionHash: result.transactionHash,
            blockNumber: result.receipt.blockNumber
        });
    } catch (error) {
        console.error(`Failed to cast vote for proposal ${proposalId}:`, error.message);
        res.status(500).json({ error: 'Failed to send vote transaction', details: error.message });
    }
});


app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});

// --- Serve Frontend Static Files ---
// Serve static files from the React app (adjust path if your frontend is elsewhere)
app.use(express.static(path.join(__dirname, '../frontend')));

// Basic GET endpoint for testing server is up (will be overridden by static serving if / is index.html)
// app.get('/', (req, res) => {
//     res.send('Backend server is running!');
// });

// The "catchall" handler: for any request that doesn't
// match one above, send back React's index.html file.
app.get('*', (req, res) => {
    // Ensure this path correctly points to your frontend's index.html
    res.sendFile(path.join(__dirname, '../frontend/index.html'));
});
