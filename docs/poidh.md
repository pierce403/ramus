# POIDH Notes

## High-level observations

- POIDH is an onchain bounty system with contracts per chain.
- The web app bundles include contract addresses, ABIs, and upload endpoints.
- The UI appears to use a tRPC API at `/api/trpc` on the same origin.

## Onchain contracts (from poidh.xyz app bundle)

Chains seen in the bundle:

- Degen chain
  - chainId: 666666666
  - main contract: `0x18e5585ca7ce31b90bc8bb7aaf84152857ce243f`
  - nft contract: `0x39f04b7897dcaf9dc454e433f43fb1c3bb528e11`

- Arbitrum One
  - chainId: 42161
  - main contract: `0x5555fa783936c260f77385b4e153b9725fef1719`
  - nft contract: `0x27E117Cc9A8DA363442e7Bd0618939E3EEEACF6A`

- Base
  - chainId: 8453
  - main contract: `0x5555fa783936c260f77385b4e153b9725fef1719`
  - nft contract: `0x27E117Cc9A8DA363442e7Bd0618939E3EEEACF6A`

Source: `https://poidh.xyz/_next/static/chunks/1200-cf0923c3fd5191d6.js`

## Key contract functions observed

- `createOpenBounty(name, description)` (payable)
- `createSoloBounty(name, description)` (payable)
- `createClaim(bountyId, name, description, uri)`
- `acceptClaim(bountyId, claimId)`
- `getClaimsByBountyId(bountyId, offset)`

These are sufficient for the bot to create bounties, monitor submissions, and award winners.

## Media / metadata upload endpoints

The front-end uses a cloud function host for uploads:

- Base URL: `https://us-central1-plated-hangout-393021.cloudfunctions.net/poidh`
- Upload image: `POST /uploadFile` (multipart form `image`)
- Upload metadata: `POST /uploadMetadata` (JSON `metadata`)

Source: `https://poidh.xyz/_next/static/chunks/1200-cf0923c3fd5191d6.js`

## tRPC API (from bundle)

The bundle references `/api/trpc` on the same origin. Procedures seen:

- `bounties.fetchAll`
- `claims.fetchAcceptedClaimByBountyId`
- `web3.fetchEnsOrDegenName`
- `neynar.usersData`

This may be useful for higher-level query APIs, but the bot can operate entirely onchain.

## Open Questions

- Confirm whether the contracts are verified and fetch ABIs from explorers.
- Confirm Poidh contract version (bundle refers to `PoidhV3`).
- Verify expected metadata format and how claim `uri` is stored and displayed.
