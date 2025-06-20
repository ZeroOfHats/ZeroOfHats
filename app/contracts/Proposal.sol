// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC721Minimal {
    function balanceOf(address owner) external view returns (uint256);
}

contract ProposalContract {

    enum ProposalStatus {
        Pending,
        Approved,
        Rejected,
        InDiscussion
    }

    struct Proposal {
        uint id;
        string description;
        address proposer;
        uint yesVotes;
        uint noVotes;
        uint abstainVotes;
        uint discussionVotes; // For "return to discussion"
        ProposalStatus status;
    }

    mapping(uint => Proposal) public proposals;
    uint public nextProposalId;
    address public nftContractAddress;

    event ProposalCreated(
        uint id,
        address indexed proposer,
        string description
    );

    event Voted(
        uint indexed proposalId,
        address indexed voter,
        uint voteType // 0: Yes, 1: No, 2: Abstain, 3: Discussion
    );

    constructor(address _nftContractAddress) {
        require(_nftContractAddress != address(0), "NFT contract address cannot be zero");
        nftContractAddress = _nftContractAddress;
        nextProposalId = 1;
    }

    function createProposal(string memory _description) public {
        proposals[nextProposalId] = Proposal({
            id: nextProposalId,
            description: _description,
            proposer: msg.sender,
            yesVotes: 0,
            noVotes: 0,
            abstainVotes: 0,
            discussionVotes: 0,
            status: ProposalStatus.Pending
        });
        emit ProposalCreated(nextProposalId, msg.sender, _description);
        nextProposalId++;
    }

    // Basic vote casting function (without NFT integration yet)
    // voteType: 0 = Yes, 1 = No, 2 = Abstain, 3 = Discussion
    function castVote(uint _proposalId, uint _voteType) public {
        require(_proposalId > 0 && _proposalId < nextProposalId, "Proposal does not exist");
        Proposal storage proposal = proposals[_proposalId];

        require(
            proposal.status == ProposalStatus.Pending || proposal.status == ProposalStatus.InDiscussion,
            "Proposal not open for voting"
        );
        require(msg.sender != proposal.proposer, "Proposer cannot vote on their own proposal");
        require(IERC721Minimal(nftContractAddress).balanceOf(msg.sender) > 0, "Voter must own an NFT");

        // Further checks (like ensuring the voter hasn't voted yet on this specific proposal) will be added later

        if (_voteType == 0) { // Yes
            proposal.yesVotes++;
        } else if (_voteType == 1) { // No
            proposal.noVotes++;
        } else if (_voteType == 2) { // Abstain
            proposal.abstainVotes++;
        } else if (_voteType == 3) { // Return to Discussion
            proposal.discussionVotes++;
        } else {
            revert("Invalid vote type");
        }
        emit Voted(_proposalId, msg.sender, _voteType);
    }
}
