# Unique NFT - ASA implementation

Based on this
[thread](https://forum.algorand.org/t/unique-nft-asa-implementation/2704);
design credits to `@fabrice`.

## Status

I have used this project to test the waters around Algorand/TEAL development
while I approached the ecosystem. The foundations are done, but there are a few
things left to improve before being "production-ready".
binary encoding format
- TODO: Add commitment-based revelation of the prime to prevent front-running
  from block selectors (MEV).
- TODO: Implement the check that `C_p` is the contract we expect encoding prime
  `p`.
- TODO: The `PRIME` argument passed to the stateful smart contract must be
  encoded through Go's
  [binary encoding format](https://golang.org/pkg/encoding/binary/#PutUvarint).
- TODO: Insert additional checks on the asset being issued and transferred (the
  NFT itself).

Also, excuse my `setup.sh` script :)
