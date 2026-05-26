// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title GiftCardGenerator
 * @notice Minimal on-chain gift card generator. Creators fund gift cards with ETH
 * and provide a hashed secret code (keccak256 of the plaintext code). The
 * recipient redeems by submitting the plaintext code which, if it matches the
 * stored hash, transfers the ETH to the redeemer and marks the gift card used.
 *
 * Usage (off-chain):
 * - Creator picks a secret code (e.g. "ABC-123-XYZ") and computes
 *   keccak256(abi.encodePacked(code)). Call `createGiftCard(codeHash, expiry)`
 *   sending ETH equal to the gift card value.
 * - To redeem, call `redeem(id, code)` with the plaintext code.
 */
contract GiftCardGenerator {
    struct GiftCard {
        address creator;
        uint256 amount; // wei funded
        bytes32 codeHash; // keccak256 hash of the secret code
        bool redeemed;
        uint256 expiry; // unix timestamp, 0 = never expire
        address redeemer;
    }

    mapping(uint256 => GiftCard) public giftCards;
    uint256 public nextId;

    event GiftCardCreated(uint256 indexed id, address indexed creator, uint256 amount, uint256 expiry);
    event GiftCardRedeemed(uint256 indexed id, address indexed redeemer, uint256 amount);
    event GiftCardWithdrawn(uint256 indexed id, address indexed creator, uint256 amount);

    /**
     * @notice Create a funded gift card.
     * @param codeHash keccak256(abi.encodePacked(code)) of the plaintext secret code
     * @param expiry unix timestamp after which the creator may withdraw the funds (0 = never)
     * @return id the gift card id
     */
    function createGiftCard(bytes32 codeHash, uint256 expiry) external payable returns (uint256) {
        require(msg.value > 0, "Must fund gift card");
        require(codeHash != bytes32(0), "Invalid code hash");
        if (expiry != 0) require(expiry > block.timestamp, "Expiry must be in future");

        nextId++;
        uint256 id = nextId;

        giftCards[id] = GiftCard({
            creator: msg.sender,
            amount: msg.value,
            codeHash: codeHash,
            redeemed: false,
            expiry: expiry,
            redeemer: address(0)
        });

        emit GiftCardCreated(id, msg.sender, msg.value, expiry);
        return id;
    }

    /**
     * @notice Redeem a funded gift card by providing the plaintext code.
     * @param id gift card id
     * @param code plaintext secret code
     */
    function redeem(uint256 id, string calldata code) external {
        GiftCard storage g = giftCards[id];
        require(g.creator != address(0), "Gift card doesn't exist");
        require(!g.redeemed, "Already redeemed");
        if (g.expiry != 0) require(block.timestamp <= g.expiry, "Expired");
        require(g.codeHash == keccak256(abi.encodePacked(code)), "Invalid code");

        g.redeemed = true;
        g.redeemer = msg.sender;

        uint256 amount = g.amount;
        g.amount = 0; // prevent reentrancy / double-spend

        (bool sent, ) = msg.sender.call{value: amount}('');
        require(sent, "Transfer failed");

        emit GiftCardRedeemed(id, msg.sender, amount);
    }

    /**
     * @notice After expiry, creator may withdraw unredeemed funds.
     */
    function withdrawUnredeemed(uint256 id) external {
        GiftCard storage g = giftCards[id];
        require(g.creator == msg.sender, "Not creator");
        require(!g.redeemed, "Already redeemed");
        require(g.expiry != 0 && block.timestamp > g.expiry, "Not expired");

        uint256 amount = g.amount;
        g.amount = 0;
        g.redeemed = true; // mark as used so it cannot be withdrawn twice

        (bool sent, ) = msg.sender.call{value: amount}('');
        require(sent, "Transfer failed");

        emit GiftCardWithdrawn(id, msg.sender, amount);
    }

    /**
     * @notice Get basic gift card info.
     */
    function getGiftCard(uint256 id) external view returns (address creator, uint256 amount, bool redeemed, uint256 expiry, address redeemer) {
        GiftCard storage g = giftCards[id];
        require(g.creator != address(0), "Gift card doesn't exist");
        return (g.creator, g.amount, g.redeemed, g.expiry, g.redeemer);
    }

    // Allow the contract to receive ETH directly
    receive() external payable {}
    fallback() external payable {}
}
