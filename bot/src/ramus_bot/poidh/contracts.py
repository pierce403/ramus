from __future__ import annotations

POIDH_CHAIN_CONFIG = {
    "base": {
        "chain_id": 8453,
        "currency": "eth",
        "main_contract": "0x5555fa783936c260f77385b4e153b9725fef1719",
        "nft_contract": "0x27E117Cc9A8DA363442e7Bd0618939E3EEEACF6A",
    },
    "arbitrum": {
        "chain_id": 42161,
        "currency": "eth",
        "main_contract": "0x5555fa783936c260f77385b4e153b9725fef1719",
        "nft_contract": "0x27E117Cc9A8DA363442e7Bd0618939E3EEEACF6A",
    },
    "degen": {
        "chain_id": 666666666,
        "currency": "degen",
        "main_contract": "0x18e5585ca7ce31b90bc8bb7aaf84152857ce243f",
        "nft_contract": "0x39f04b7897dcaf9dc454e433f43fb1c3bb528e11",
    },
}

POIDH_MINIMAL_ABI = [
    {
        "inputs": [],
        "name": "bountyCounter",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "string", "name": "description", "type": "string"},
        ],
        "name": "createSoloBounty",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "string", "name": "description", "type": "string"},
        ],
        "name": "createOpenBounty",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "bountyId", "type": "uint256"},
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "string", "name": "description", "type": "string"},
            {"internalType": "string", "name": "uri", "type": "string"},
        ],
        "name": "createClaim",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "bountyId", "type": "uint256"},
            {"internalType": "uint256", "name": "claimId", "type": "uint256"},
        ],
        "name": "acceptClaim",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "bountyId", "type": "uint256"},
            {"internalType": "uint256", "name": "offset", "type": "uint256"},
        ],
        "name": "getClaimsByBountyId",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "id", "type": "uint256"},
                    {"internalType": "address", "name": "issuer", "type": "address"},
                    {"internalType": "uint256", "name": "bountyId", "type": "uint256"},
                    {"internalType": "address", "name": "bountyIssuer", "type": "address"},
                    {"internalType": "string", "name": "name", "type": "string"},
                    {"internalType": "string", "name": "description", "type": "string"},
                    {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                    {"internalType": "bool", "name": "accepted", "type": "bool"},
                ],
                "internalType": "struct PoidhV3.Claim[]",
                "name": "",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "offset", "type": "uint256"}],
        "name": "getBounties",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "id", "type": "uint256"},
                    {"internalType": "address", "name": "issuer", "type": "address"},
                    {"internalType": "string", "name": "name", "type": "string"},
                    {"internalType": "string", "name": "description", "type": "string"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                    {"internalType": "address", "name": "claimer", "type": "address"},
                    {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                    {"internalType": "uint256", "name": "claimId", "type": "uint256"},
                ],
                "internalType": "struct PoidhV3.Bounty[]",
                "name": "",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getBountiesLength",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]
