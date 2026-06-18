# codec spec (fixture)

- `encode` / `decode` **MUST** round-trip **exactly**: `decode(encode(fields)) == fields`
  byte-for-byte, **including any trailing empty field**. The comparison must not normalize
  (no `rstrip`/`strip`/`lower`/`sorted`) — exactness is the contract.
- `case_fold` is case-insensitive by contract: it lowercases its input. (Lowercasing here is
  intended behaviour, not a normalization papering over a delta.)
