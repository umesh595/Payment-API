#!/usr/bin/env python3
"""
Production test scenarios for Payment API (Async version).
All endpoints use /api/ prefix and JWT authentication.
Direct async conversion - same logic as sync version.
"""

import asyncio
import aiohttp
import argparse
import time
import random
import sys


class ScenarioRunner:
    def __init__(self, base_url: str, customer_id: str, password: str = "Test@123"):
        self.base_url = base_url.rstrip("/")
        self.customer_id = customer_id
        self.password = password
        self.token = None
        self.headers = None
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry - create aiohttp session."""
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close session."""
        if self.session:
            await self.session.close()
    
    async def _safe_json(self, response, key, default=None):
        """Safely extract key from JSON response."""
        try:
            if response.status == 200:
                data = await response.json()
                return data.get(key, default)
        except:
            pass
        return default
    
    async def register_user(self):
        """Register user if not exists."""
        print(f"Registering user {self.customer_id}...")
        
        async with self.session.post(
            f"{self.base_url}/api/auth/register",
            json={
                "user_id": self.customer_id,
                "email": f"{self.customer_id.lower()}@example.com",
                "full_name": f"Test User {self.customer_id}",
                "phone": "+91-9876543210",
                "password": self.password,
            },
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status in (200, 201):
                print("✓ User registered")
            elif response.status == 400:
                print("✓ User already exists")
            else:
                text = await response.text()
                print(f"✗ Registration failed: {response.status} - {text[:100]}")
    
    async def login(self):
        """Login and get JWT token."""
        print(f"Logging in as {self.customer_id}...")
        
        async with self.session.post(
            f"{self.base_url}/api/auth/login",
            json={
                "user_id": self.customer_id,
                "password": self.password
            },
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.token = data["access_token"]
                self.headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                print("✓ Login successful")
                return True
            else:
                text = await response.text()
                print(f"✗ Login failed: {response.status} - {text[:100]}")
                return False
    
    async def ensure_wallet(self):
        """Ensure wallet exists with minimum balance."""
        await self.register_user()
        
        if not await self.login():
            print("✗ Cannot proceed without authentication")
            return False
        
        print(f"Ensuring wallet for {self.customer_id}...")
        
        async with self.session.get(
            f"{self.base_url}/api/wallet/{self.customer_id}",
            headers=self.headers
        ) as response:
            if response.status == 200:
                balance = await self._safe_json(response, "balance", 0)
                print(f"✓ Wallet balance: {balance}")
                if balance < 500:
                    print("Topping up wallet...")
                    await self._credit_wallet(1000.0 - balance)
                return True
            elif response.status == 404:
                print("Creating wallet...")
                return await self._credit_wallet(1000.0)
            else:
                print(f"✗ Wallet check failed: {response.status}")
                return False
    
    async def _credit_wallet(self, amount):
        """Internal: Credit wallet."""
        try:
            async with self.session.post(
                f"{self.base_url}/api/wallet/{self.customer_id}/credit",
                json={"amount": amount},
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    balance = await self._safe_json(resp, "balance")
                    print(f"✓ Credited {amount}, balance: {balance}")
                    return True
        except Exception as e:
            print(f"✗ Credit error: {e}")
        return False
    
    async def _debit_wallet(self, amount):
        """Internal: Debit wallet."""
        try:
            async with self.session.post(
                f"{self.base_url}/api/wallet/{self.customer_id}/debit",
                json={"amount": amount},
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    balance = await self._safe_json(resp, "balance")
                    print(f"✓ Debited {amount}, balance: {balance}")
                    return True
        except Exception as e:
            print(f"✗ Debit error: {e}")
        return False
    
    async def _create_order(self, amount, currency="INR"):
        """Internal: Create order."""
        try:
            async with self.session.post(
                f"{self.base_url}/api/orders",
                json={
                    "customer_id": self.customer_id,
                    "amount": amount,
                    "currency": currency
                },
                headers=self.headers
            ) as resp:
                if resp.status == 201:
                    print(f"✓ Order created: {amount} {currency}")
                    return True
        except Exception as e:
            print(f"✗ Order error: {e}")
        return False
    
    async def _get_wallet_balance(self):
        """Internal: Get wallet balance safely."""
        try:
            async with self.session.get(
                f"{self.base_url}/api/wallet/{self.customer_id}",
                headers=self.headers
            ) as resp:
                return await self._safe_json(resp, "balance", 0.0)
        except:
            return 0.0
    
    async def _get_orders_count(self):
        """Internal: Get orders count safely."""
        try:
            async with self.session.get(
                f"{self.base_url}/api/orders?customer_id={self.customer_id}",
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return len(data)
        except:
            pass
        return 0
    
    async def mixed(self):
        """Mixed operations scenario."""
        print("\n=== Running mixed scenario ===")
        
        if not await self.ensure_wallet():
            print("✗ Setup failed")
            return
        
        operations = [
            ("credit", 200.0),
            ("order", 150.0),
            ("debit", 50.0),
            ("order", 300.0),
            ("credit", 100.0),
        ]
        
        random.shuffle(operations)
        
        for op_type, amount in operations:
            if op_type == "credit":
                print(f"\nCrediting {amount}...")
                await self._credit_wallet(amount)
            elif op_type == "debit":
                print(f"\nDebiting {amount}...")
                await self._debit_wallet(amount)
            elif op_type == "order":
                print(f"\nCreating order for {amount}...")
                await self._create_order(amount)
            
            await asyncio.sleep(0.2)  # ✅ Async sleep
        
        print("\n=== Final state ===")
        balance = await self._get_wallet_balance()
        print(f"Wallet balance: {balance}")
        
        order_count = await self._get_orders_count()
        print(f"Total orders: {order_count}")
    
    async def orders_retry(self):
        """Idempotency test scenario."""
        print("\n=== Running orders_retry scenario ===")
        
        if not await self.ensure_wallet():
            return
        
        idempotency_key = f"retry-{int(time.time())}"
        payload = {
            "customer_id": self.customer_id,
            "amount": 499.99,
            "currency": "INR",
            "idempotency_key": idempotency_key
        }
        
        print(f"Attempt 1 with key: {idempotency_key}")
        async with self.session.post(
            f"{self.base_url}/api/orders",
            json=payload,
            headers=self.headers
        ) as resp1:
            print(f"Response 1: {resp1.status}")
        
        print(f"Attempt 2 (same key)...")
        async with self.session.post(
            f"{self.base_url}/api/orders",
            json=payload,
            headers=self.headers
        ) as resp2:
            print(f"Response 2: {resp2.status}")
        
        await asyncio.sleep(1)  # ✅ Async sleep
        
        # Count orders with this idempotency key
        async with self.session.get(
            f"{self.base_url}/api/orders?customer_id={self.customer_id}",
            headers=self.headers
        ) as resp:
            if resp.status == 200:
                orders = await resp.json()
            else:
                orders = []
        
        matching = [o for o in orders if o.get("idempotency_key") == idempotency_key]
        print(f"Orders with key '{idempotency_key}': {len(matching)} (expected: 1)")


async def run_scenario(args):
    """Run the selected scenario asynchronously."""
    async with ScenarioRunner(
        base_url=args.base_url,
        customer_id=args.customer_id,
        password=args.password
    ) as runner:
        if args.scenario == "mixed":
            await runner.mixed()
        elif args.scenario == "orders_retry":
            await runner.orders_retry()
        else:
            print(f"Unknown scenario: {args.scenario}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Payment API Test Scenarios (Async)")
    
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL"
    )
    
    parser.add_argument(
        "--customer-id",
        default="CUST-001",
        help="Customer ID to test with"
    )
    
    parser.add_argument(
        "--password",
        default="Test@123",
        help="Password for the test user"
    )
    
    parser.add_argument(
        "--scenario",
        default="mixed",
        choices=["mixed", "orders_retry"],
        help="Scenario to run (default: mixed)"
    )
    
    args = parser.parse_args()
    
    # ✅ Run async main
    asyncio.run(run_scenario(args))


if __name__ == "__main__":
    main()