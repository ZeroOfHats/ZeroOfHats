document.addEventListener('DOMContentLoaded', () => {
    const informForm = document.getElementById('inform-form');
    const informTopicInput = document.getElementById('inform-topic');
    const informKnowledgeInput = document.getElementById('inform-knowledge');
    const informMessagesDiv = document.getElementById('inform-messages');
    const submitInformButton = document.getElementById('submit-inform');

    // Discussion section elements
    const newDiscussionForm = document.getElementById('new-discussion-form');
    const discussionTitleInput = document.getElementById('discussion-title');
    const discussionInitialCommentInput = document.getElementById('discussion-initial-comment');
    const discussionUserIdInput = document.getElementById('discussion-user-id');
    const submitDiscussionButton = document.getElementById('submit-discussion');
    const discussionFormMessagesDiv = document.getElementById('discussion-form-messages');

    const loadDiscussionsButton = document.getElementById('load-discussions-button');
    const discussionsListDiv = document.getElementById('discussions-list');
    const discussionsListMessagesDiv = document.getElementById('discussions-list-messages');

    // Discussion Detail Area elements
    const discussionDetailArea = document.getElementById('discussion-detail-area');
    const selectedDiscussionTitleSpan = document.getElementById('selected-discussion-title');
    const commentsListDiv = document.getElementById('comments-list');
    const commentsListMessagesDiv = document.getElementById('comments-list-messages');

    // New Comment Form elements
    const newCommentForm = document.getElementById('new-comment-form');
    const commentTextInput = document.getElementById('comment-text');
    const commentUserIdInput = document.getElementById('comment-user-id');
    const currentDiscussionIdInput = document.getElementById('current-discussion-id-for-comment');
    const submitCommentButton = document.getElementById('submit-comment');
    const commentFormMessagesDiv = document.getElementById('comment-form-messages');

    let activeDiscussionId = null; // To store the currently selected discussion ID
    let discussionTitlesCache = {}; // To store titles for quick lookup

    // Propose & Vote Section elements
    const mintNftForm = document.getElementById('mint-nft-form'); // Though button is type button, can still group
    const nftRecipientAddressInput = document.getElementById('nft-recipient-address');
    const mintNftButton = document.getElementById('mint-nft-button');
    const mintNftMessagesDiv = document.getElementById('mint-nft-messages');

    const newProposalForm = document.getElementById('new-proposal-form');
    const proposalDescriptionInput = document.getElementById('proposal-description');
    const submitProposalButton = document.getElementById('submit-proposal');
    const proposalFormMessagesDiv = document.getElementById('proposal-form-messages');

    const loadProposalsButton = document.getElementById('load-proposals-button');
    const proposalsListDiv = document.getElementById('proposals-list');
    const proposalsListMessagesDiv = document.getElementById('proposals-list-messages');


    // Base URL for the API. Adjust if your backend runs on a different port or host.
    const API_BASE_URL = 'http://localhost:3000/api';

    if (informForm) {
        informForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            submitInformButton.disabled = true;
            informMessagesDiv.innerHTML = ''; // Clear previous messages
            informMessagesDiv.className = 'messages'; // Reset class

            const topic = informTopicInput.value.trim();
            const knowledge = informKnowledgeInput.value.trim();

            if (!topic || !knowledge) {
                displayMessage('Topic and Knowledge fields are required.', 'error', informMessagesDiv);
                submitInformButton.disabled = false;
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/inform`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ topic, knowledge }),
                });

                const result = await response.json();

                if (response.ok) {
                    displayMessage(`Success: ${result.message}. Topic: ${result.topic}, Knowledge: ${result.knowledge}`, 'success', informMessagesDiv);
                    informForm.reset(); // Clear the form
                } else {
                    displayMessage(`Error: ${result.error || 'An unknown error occurred.'} (Status: ${response.status})`, 'error', informMessagesDiv);
                }
            } catch (error) {
                console.error('Error submitting inform data:', error);
                displayMessage(`Network Error: Could not connect to the server. ${error.message}`, 'error', informMessagesDiv);
            } finally {
                submitInformButton.disabled = false;
            }
        });
    }

    function displayMessage(message, type, element) {
        element.innerHTML = message;
        element.className = `messages ${type}`; // Applies .success or .error styling
    }

    // --- Placeholder for Web3/Ethers.js integration ---
    async function connectWallet() {
        if (typeof window.ethereum !== 'undefined') {
            try {
                // Request account access
                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                const account = accounts[0];
                console.log('Connected account:', account);
                // You can now instantiate ethers provider and signer
                // const provider = new ethers.providers.Web3Provider(window.ethereum);
                // const signer = provider.getSigner();
                displayMessage(`Wallet connected: ${account}`, 'success', document.getElementById('wallet-messages')); // Assuming a div for wallet messages
            } catch (error) {
                console.error('Error connecting wallet:', error);
                displayMessage(`Error connecting wallet: ${error.message}`, 'error', document.getElementById('wallet-messages'));
            }
        } else {
            displayMessage('MetaMask (or other Web3 wallet) not detected. Please install it.', 'error', document.getElementById('wallet-messages'));
        }
    }

    // Example: Add a connect wallet button listener if you add such a button
    // const connectWalletButton = document.getElementById('connect-wallet-button');
    // if (connectWalletButton) {
    //     connectWalletButton.addEventListener('click', connectWallet);
    // }

    // --- "Discuss" Section Logic ---
    const INFORM_POST_ID_PLACEHOLDER = 'test-inform-post-123'; // Placeholder

    if (newDiscussionForm) {
        newDiscussionForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            submitDiscussionButton.disabled = true;
            discussionFormMessagesDiv.innerHTML = '';
            discussionFormMessagesDiv.className = 'messages';

            const title = discussionTitleInput.value.trim();
            const initialComment = discussionInitialCommentInput.value.trim();
            const userId = discussionUserIdInput.value.trim(); // In a real app, this might come from auth state

            if (!title || !initialComment || !userId) {
                displayMessage('All fields (Title, Initial Comment, User ID) are required.', 'error', discussionFormMessagesDiv);
                submitDiscussionButton.disabled = false;
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/inform/${INFORM_POST_ID_PLACEHOLDER}/discussions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, initialComment, userId }),
                });
                const result = await response.json();
                if (response.ok) {
                    displayMessage(`Discussion "${result.title}" created successfully! (ID: ${result.discussionId})`, 'success', discussionFormMessagesDiv);
                    newDiscussionForm.reset();
                    loadDiscussions(INFORM_POST_ID_PLACEHOLDER); // Refresh the list
                } else {
                    displayMessage(`Error creating discussion: ${result.error || 'Unknown error'}`, 'error', discussionFormMessagesDiv);
                }
            } catch (error) {
                console.error('Error submitting new discussion:', error);
                displayMessage(`Network Error: ${error.message}`, 'error', discussionFormMessagesDiv);
            } finally {
                submitDiscussionButton.disabled = false;
            }
        });
    }

    async function loadDiscussions(informPostId) {
        if (!informPostId) {
            displayMessage('Cannot load discussions without an Inform Post ID.', 'error', discussionsListMessagesDiv);
            return;
        }
        discussionsListDiv.innerHTML = 'Loading discussions...'; // Show loading state
        discussionsListMessagesDiv.innerHTML = '';
        discussionsListMessagesDiv.className = 'messages';

        try {
            const response = await fetch(`${API_BASE_URL}/inform/${informPostId}/discussions`);
            if (!response.ok) {
                const errorResult = await response.json().catch(() => ({ error: 'Failed to fetch discussions.' }));
                throw new Error(errorResult.error || `HTTP error! Status: ${response.status}`);
            }
            const discussions = await response.json();

            discussionsListDiv.innerHTML = ''; // Clear loading state or previous list
            if (discussions.length === 0) {
                discussionsListDiv.innerHTML = '<p>No discussions found for this topic yet.</p>';
                return;
            }

            const ul = document.createElement('ul');
            ul.className = 'discussion-items-list';
            discussionTitlesCache = {}; // Clear cache before loading
            discussions.forEach(discussion => {
                discussionTitlesCache[discussion.id] = discussion.title; // Cache title
                const li = document.createElement('li');
                li.dataset.discussionId = discussion.id;
                li.setAttribute('tabindex', '0'); // Make it focusable for accessibility
                li.className = 'discussion-item'; // For styling and event delegation
                li.innerHTML = `
                    <h4>${discussion.title}</h4>
                    <p>Comments: ${discussion.commentCount || 0}</p>
                    <small>Created: ${new Date(discussion.createdAt).toLocaleString()}</small>
                `;
                ul.appendChild(li);
            });
            discussionsListDiv.appendChild(ul);

        } catch (error) {
            console.error('Error loading discussions:', error);
            displayMessage(`Error loading discussions: ${error.message}`, 'error', discussionsListMessagesDiv);
            discussionsListDiv.innerHTML = '<p>Could not load discussions.</p>';
        }
    }

    if (discussionsListDiv) {
        discussionsListDiv.addEventListener('click', (event) => {
            const clickedItem = event.target.closest('.discussion-item');
            if (clickedItem && clickedItem.dataset.discussionId) {
                activeDiscussionId = clickedItem.dataset.discussionId;
                currentDiscussionIdInput.value = activeDiscussionId;
                const title = discussionTitlesCache[activeDiscussionId] || 'Selected Discussion';
                selectedDiscussionTitleSpan.textContent = title;
                discussionDetailArea.style.display = 'block';
                loadComments(activeDiscussionId);
            }
        });
         // Add keyboard accessibility for discussion items
        discussionsListDiv.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                const clickedItem = event.target.closest('.discussion-item');
                if (clickedItem && clickedItem.dataset.discussionId) {
                    event.preventDefault(); // Prevent scrolling if space is pressed
                    activeDiscussionId = clickedItem.dataset.discussionId;
                    currentDiscussionIdInput.value = activeDiscussionId;
                    const title = discussionTitlesCache[activeDiscussionId] || 'Selected Discussion';
                    selectedDiscussionTitleSpan.textContent = title;
                    discussionDetailArea.style.display = 'block';
                    loadComments(activeDiscussionId);
                }
            }
        });
    }

    async function loadComments(discussionId) {
        if (!discussionId) {
            displayMessage('No discussion selected to load comments.', 'error', commentsListMessagesDiv);
            return;
        }
        commentsListDiv.innerHTML = 'Loading comments...';
        commentsListMessagesDiv.innerHTML = '';
        commentsListMessagesDiv.className = 'messages';

        try {
            const response = await fetch(`${API_BASE_URL}/discussions/${discussionId}/comments`);
            if (!response.ok) {
                const errorResult = await response.json().catch(() => ({error: 'Failed to load comments.'}));
                throw new Error(errorResult.error || `HTTP error! Status: ${response.status}`);
            }
            const comments = await response.json();
            commentsListDiv.innerHTML = ''; // Clear loading state

            if (comments.length === 0) {
                commentsListDiv.innerHTML = '<p>No comments yet for this discussion.</p>';
                return;
            }
            const ul = document.createElement('ul');
            ul.className = 'comments-items-list';
            comments.forEach(comment => {
                const li = document.createElement('li');
                li.className = 'comment-item';
                // Assuming comment object has `userId` and `text` (or `commentText`) and `createdAt`
                li.innerHTML = `
                    <p><strong>User ${comment.userId || 'Anonymous'}:</strong> ${comment.text || comment.commentText}</p>
                    <small>Posted: ${new Date(comment.createdAt).toLocaleString()}</small>
                `;
                ul.appendChild(li);
            });
            commentsListDiv.appendChild(ul);
        } catch (error) {
            console.error(`Error loading comments for discussion ${discussionId}:`, error);
            displayMessage(`Error loading comments: ${error.message}`, 'error', commentsListMessagesDiv);
            commentsListDiv.innerHTML = '<p>Could not load comments.</p>';
        }
    }

    if (newCommentForm) {
        newCommentForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            submitCommentButton.disabled = true;
            commentFormMessagesDiv.innerHTML = '';
            commentFormMessagesDiv.className = 'messages';

            const commentText = commentTextInput.value.trim();
            const userId = commentUserIdInput.value.trim(); // Placeholder
            const discussionId = currentDiscussionIdInput.value; // From hidden input

            if (!commentText || !userId) {
                displayMessage('Comment text and User ID are required.', 'error', commentFormMessagesDiv);
                submitCommentButton.disabled = false;
                return;
            }
            if (!discussionId) {
                displayMessage('No discussion selected to comment on. Please click a discussion first.', 'error', commentFormMessagesDiv);
                submitCommentButton.disabled = false;
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/discussions/${discussionId}/comments`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId, commentText }),
                });
                const result = await response.json();
                if (response.ok) {
                    displayMessage('Comment added successfully!', 'success', commentFormMessagesDiv);
                    newCommentForm.reset(); // Clear form fields
                    // commentUserIdInput.value = userId; // Optionally persist user ID if needed
                    loadComments(discussionId); // Refresh comments list
                } else {
                    displayMessage(`Error adding comment: ${result.error || 'Unknown error'}`, 'error', commentFormMessagesDiv);
                }
            } catch (error) {
                console.error('Error submitting new comment:', error);
                displayMessage(`Network Error: ${error.message}`, 'error', commentFormMessagesDiv);
            } finally {
                submitCommentButton.disabled = false;
            }
        });
    }

    if (loadDiscussionsButton) {
        loadDiscussionsButton.addEventListener('click', () => {
            // For now, using a placeholder. In a real app, you'd get this from context.
            loadDiscussions(INFORM_POST_ID_PLACEHOLDER);
        });
    }

    // Initial load of discussions when the page is ready
    // You might want to tie this to a specific "inform" post being selected by the user eventually.
    loadDiscussions(INFORM_POST_ID_PLACEHOLDER);


    // --- "Propose & Vote" Section Logic ---

    if (mintNftButton) {
        mintNftButton.addEventListener('click', async () => {
            mintNftButton.disabled = true;
            mintNftMessagesDiv.innerHTML = '';
            mintNftMessagesDiv.className = 'messages';
            const recipientAddress = nftRecipientAddressInput.value.trim();

            if (!recipientAddress) { // Basic validation, ethers.isAddress is better for real use
                displayMessage('Please enter a valid Ethereum address.', 'error', mintNftMessagesDiv);
                mintNftButton.disabled = false;
                return;
            }
            // A more robust validation can be added here using ethers.js if it's also loaded in frontend
            // For now, simple check:
            if (!/^0x[a-fA-F0-9]{40}$/.test(recipientAddress)) {
                 displayMessage('Invalid Ethereum address format.', 'error', mintNftMessagesDiv);
                 mintNftButton.disabled = false;
                 return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/nfts/mint`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ recipientAddress }),
                });
                const result = await response.json();
                if (response.ok) {
                    displayMessage(`NFT Minting TX Sent: ${result.transactionHash}. Block: ${result.blockNumber}`, 'success', mintNftMessagesDiv);
                    nftRecipientAddressInput.value = ''; // Clear input
                } else {
                    displayMessage(`Error minting NFT: ${result.error || 'Unknown error'}`, 'error', mintNftMessagesDiv);
                }
            } catch (error) {
                console.error('Error minting NFT:', error);
                displayMessage(`Network Error: ${error.message}`, 'error', mintNftMessagesDiv);
            } finally {
                mintNftButton.disabled = false;
            }
        });
    }

    if (newProposalForm) {
        newProposalForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            submitProposalButton.disabled = true;
            proposalFormMessagesDiv.innerHTML = '';
            proposalFormMessagesDiv.className = 'messages';

            const description = proposalDescriptionInput.value.trim();
            if (!description) {
                displayMessage('Proposal description cannot be empty.', 'error', proposalFormMessagesDiv);
                submitProposalButton.disabled = false;
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/proposals`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ description }),
                });
                const result = await response.json();
                if (response.ok) {
                    displayMessage(`Proposal TX Sent: ${result.transactionHash}. Block: ${result.blockNumber}`, 'success', proposalFormMessagesDiv);
                    proposalDescriptionInput.value = ''; // Clear textarea
                    loadProposals(); // Refresh proposal list
                } else {
                    displayMessage(`Error creating proposal: ${result.error || 'Unknown error'}`, 'error', proposalFormMessagesDiv);
                }
            } catch (error) {
                console.error('Error creating proposal:', error);
                displayMessage(`Network Error: ${error.message}`, 'error', proposalFormMessagesDiv);
            } finally {
                submitProposalButton.disabled = false;
            }
        });
    }

    const proposalStatusMap = { // Helper to map status numbers to text
        0: 'Pending',
        1: 'Approved',
        2: 'Rejected',
        3: 'InDiscussion'
    };

    async function loadProposals() {
        proposalsListDiv.innerHTML = 'Loading proposals...';
        proposalsListMessagesDiv.innerHTML = '';
        proposalsListMessagesDiv.className = 'messages';

        try {
            const response = await fetch(`${API_BASE_URL}/proposals`);
            if (!response.ok) {
                const errorResult = await response.json().catch(() => ({ error: 'Failed to fetch proposals.' }));
                throw new Error(errorResult.error || `HTTP error! Status: ${response.status}`);
            }
            const proposals = await response.json();
            proposalsListDiv.innerHTML = ''; // Clear loading/previous

            if (proposals.length === 0) {
                proposalsListDiv.innerHTML = '<p>No proposals found yet.</p>';
                return;
            }

            proposals.forEach(proposal => {
                const article = document.createElement('article');
                article.className = 'proposal-item';
                article.dataset.proposalId = proposal.id;

                let votesHtml = '<div class="vote-buttons">';
                // Vote types: 0: Yes, 1: No, 2: Abstain, 3: Discussion
                const voteOptions = [
                    { label: 'Yes', type: 0 },
                    { label: 'No', type: 1 },
                    { label: 'Abstain', type: 2 },
                    { label: 'To Discussion', type: 3 }
                ];
                voteOptions.forEach(opt => {
                    votesHtml += `<button class="vote-button" data-proposal-id="${proposal.id}" data-vote-type="${opt.type}">${opt.label}</button>`;
                });
                votesHtml += '</div>';

                article.innerHTML = `
                    <h4>Proposal #${proposal.id}</h4>
                    <p><strong>Description:</strong> ${proposal.description}</p>
                    <p><strong>Proposer:</strong> ${proposal.proposer}</p>
                    <p>
                        <strong>Votes:</strong>
                        Yes: ${proposal.yesVotes},
                        No: ${proposal.noVotes},
                        Abstain: ${proposal.abstainVotes},
                        Discussion: ${proposal.discussionVotes}
                    </p>
                    <p><strong>Status:</strong> ${proposalStatusMap[proposal.status] || 'Unknown'}</p>
                    ${votesHtml}
                    <div class="proposal-vote-messages" id="proposal-vote-messages-${proposal.id}"></div>
                `;
                proposalsListDiv.appendChild(article);
            });

        } catch (error) {
            console.error('Error loading proposals:', error);
            displayMessage(`Error loading proposals: ${error.message}`, 'error', proposalsListMessagesDiv);
            proposalsListDiv.innerHTML = '<p>Could not load proposals.</p>';
        }
    }

    if (loadProposalsButton) {
        loadProposalsButton.addEventListener('click', loadProposals);
    }

    // Initial load of proposals
    loadProposals();

    // --- Handle Vote Button Clicks ---
    if (proposalsListDiv) {
        proposalsListDiv.addEventListener('click', async (event) => {
            const voteButton = event.target.closest('.vote-button');
            if (!voteButton) {
                return; // Click was not on a vote button
            }

            const proposalId = voteButton.dataset.proposalId;
            const voteType = parseInt(voteButton.dataset.voteType, 10); // Ensure it's a number

            if (proposalId === undefined || isNaN(voteType)) {
                console.error('Missing proposal ID or vote type on button.');
                return;
            }

            const proposalMessagesDiv = document.getElementById(`proposal-vote-messages-${proposalId}`);
            if (!proposalMessagesDiv) {
                console.error(`Could not find message area for proposal ${proposalId}`);
                return;
            }

            // Disable all vote buttons for this proposal during voting
            const allVoteButtonsForProposal = proposalsListDiv.querySelectorAll(`.vote-button[data-proposal-id="${proposalId}"]`);
            allVoteButtonsForProposal.forEach(btn => btn.disabled = true);

            displayMessage('Processing vote...', 'info', proposalMessagesDiv); // 'info' class can be generic

            try {
                const response = await fetch(`${API_BASE_URL}/proposals/${proposalId}/vote`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ voteType }), // Backend expects voteType as a number
                });

                const result = await response.json();

                if (response.ok) {
                    displayMessage(`Vote successfully cast! TX: ${result.transactionHash}`, 'success', proposalMessagesDiv);
                    // Refreshing the whole list will re-enable buttons and show new counts
                    loadProposals();
                } else {
                    displayMessage(`Error casting vote: ${result.error || 'Unknown error'}`, 'error', proposalMessagesDiv);
                    // Re-enable buttons only on error if not refreshing
                    allVoteButtonsForProposal.forEach(btn => btn.disabled = false);
                }
            } catch (error) {
                console.error('Error casting vote:', error);
                displayMessage(`Network Error: ${error.message}`, 'error', proposalMessagesDiv);
                allVoteButtonsForProposal.forEach(btn => btn.disabled = false); // Re-enable on network error
            }
            // No finally block to re-enable buttons if loadProposals() is called on success,
            // as it will rebuild the buttons. If loadProposals() was conditional, a finally block would be needed.
        });
    }
});
