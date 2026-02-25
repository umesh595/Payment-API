#!/usr/bin/env python3
"""
Data seeding script for Payment API (Async version).
Uses /api/ prefix and public registration endpoint.
Direct async conversion - same logic as sync version.
"""

import asyncio
import aiohttp
import sys

BASE_URL = "http://localhost:8000"
DEFAULT_PASSWORD = "Seed@123"


async def seed_user(session: aiohttp.ClientSession, base_url: str, user_id: str, email: str, full_name: str, phone: str, password: str):
    """Create a user via public registration endpoint."""
    print(f"Creating user {user_id}...")
    
    try:
        async with session.post(
            f"{base_url}/api/auth/register",
            json={
                "user_id": user_id,
                "email": email,
                "full_name": full_name,
                "phone": phone,
                "password": password
            },
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 201:
                data = await response.json()
                print(f"✓ User created: {data['user_id']}")
                return True
            elif response.status == 400:
                print(f"✓ User {user_id} already exists")
                return True
            else:
                text = await response.text()
                print(f"✗ Failed to create user: {response.status} - {text[:100]}")
                return False
    except Exception as e:
        print(f"✗ User creation error: {e}")
        return False


async def login_for_token(session: aiohttp.ClientSession, base_url: str, user_id: str, password: str):
    """Login and return JWT token for protected endpoints."""
    try:
        async with session.post(
            f"{base_url}/api/auth/login",
            json={"user_id": user_id, "password": password},
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                token = data["access_token"]
                return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            else:
                text = await response.text()
                print(f"✗ Login failed for {user_id}: {response.status} - {text[:100]}")
                print(f"   Tip: Ensure '{user_id}' was registered with password '{password}'")
                return None
    except Exception as e:
        print(f"✗ Login error for {user_id}: {e}")
        return None


async def seed_wallet(session: aiohttp.ClientSession, base_url: str, customer_id: str, initial_balance: float, password: str):
    """Initialize a wallet with starting balance (requires auth)."""
    print(f"Seeding wallet for {customer_id} with balance {initial_balance}...")
    
    headers = await login_for_token(session, base_url, customer_id, password)
    if not headers:
        return False
    
    try:
        async with session.post(
            f"{base_url}/api/wallet/{customer_id}/credit",
            json={"amount": initial_balance},
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✓ Wallet credited: {data['customer_id']} - Balance: {data['balance']}")
                return True
            else:
                text = await response.text()
                print(f"✗ Failed to credit wallet: {response.status} - {text[:100]}")
                return False
    except Exception as e:
        print(f"✗ Wallet credit error: {e}")
        return False


async def seed_orders(session: aiohttp.ClientSession, base_url: str, customer_id: str, count: int, password: str):
    """Create sample orders (requires auth)."""
    print(f"\nCreating {count} sample orders for {customer_id}...")
    
    headers = await login_for_token(session, base_url, customer_id, password)
    if not headers:
        return False
    
    for i in range(count):
        amount = 100.0 + (i * 50)
        try:
            async with session.post(
                f"{base_url}/api/orders",
                json={
                    "customer_id": customer_id,
                    "amount": amount,
                    "currency": "INR",
                    "idempotency_key": f"seed-order-{customer_id}-{i}"
                },
                headers=headers
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    print(f"✓ Order created: {data['order_id']}")
                elif response.status == 400:
                    text = await response.text()
                    print(f"⚠ Order skipped (validation): {text[:100]}")
                else:
                    text = await response.text()
                    print(f"✗ Failed to create order: {response.status} - {text[:100]}")
        except Exception as e:
            print(f"✗ Order creation error: {e}")
        await asyncio.sleep(0.05)  # Small delay between requests


async def seed_single_user(base_url: str, customer_id: str, email: str, full_name: str, phone: str, password: str):
    """Seed a single user with wallet and orders."""
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        if await seed_user(session, base_url, customer_id, email, full_name, phone, password):
            await seed_wallet(session, base_url, customer_id, 1000.0, password)
            await seed_orders(session, base_url, customer_id, 3, password)


async def seed_multiple_users(base_url: str, password: str):
    """Seed multiple sample users."""
    users = [
        ("CUST-001", "john@example.com", "John Doe", "+91-9876543210"),
        ("CUST-002", "jane@example.com", "Jane Smith", "+91-9876543211"),
        ("CUST-003", "bob@example.com", "Bob Wilson", "+91-9876543212"),
    ]
    
    print("=" * 60)
    print("Seeding multiple users")
    print("=" * 60)
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for user_id, email, full_name, phone in users:
            print(f"\n--- Processing {user_id} ---")
            if await seed_user(session, base_url, user_id, email, full_name, phone, password):
                balance = 1000.0 + (int(user_id.split('-')[1]) * 500)
                await seed_wallet(session, base_url, user_id, balance, password)
                await seed_orders(session, base_url, user_id, 2, password)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Seed multiple users
        password = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PASSWORD
        print(f"Starting multi-user seeding with password: {'*' * len(password)}\n")
        asyncio.run(seed_multiple_users(BASE_URL, password))
    else:
        # Seed single user - ✅ Fixed: Correct argument indexing
        # Usage: script.py customer_id email full_name phone password
        customer_id = sys.argv[1] if len(sys.argv) > 1 else "CUST-001"
        email = sys.argv[2] if len(sys.argv) > 2 else f"{customer_id.lower()}@example.com"
        full_name = sys.argv[3] if len(sys.argv) > 3 else "Test User"
        phone = sys.argv[4] if len(sys.argv) > 4 else "+91-9876543210"
        password = sys.argv[5] if len(sys.argv) > 5 else DEFAULT_PASSWORD  # ✅ Fixed: index 5, not 4
        
        print(f"Starting data seeding for customer: {customer_id}")
        print(f"Password: {'*' * len(password)}")
        print()
        
        asyncio.run(seed_single_user(BASE_URL, customer_id, email, full_name, phone, password))
        
        print("\n✓ Seeding complete!")


if __name__ == "__main__":
    main()