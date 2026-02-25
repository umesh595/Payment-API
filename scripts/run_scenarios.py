#!/usr/bin/env python3
"""
Production test scenarios for Payment API.
All endpoints use /api/ prefix and JWT authentication.
"""

import requests
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
        self.headers = None  # Will be set after login
    
    def _safe_json(self, response, key, default=None):
        """Safely extract key from JSON response."""
        try:
            if response.status_code == 200:
                data = response.json()
                return data.get(key, default)
        except:
            pass
        return default
    
    def register_user(self):
        """Register user if not exists."""
        print(f"Registering user {self.customer_id}...")
        
        response = requests.post(
            f"{self.base_url}/api/auth/register",
            json={
                "user_id": self.customer_id,
                "email": f"{self.customer_id.lower()}@example.com",
                "full_name": f"Test User {self.customer_id}",
                "phone": "+91-9876543210",
                "password": self.password,
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code in (200, 201):
            print("✓ User registered")
        elif response.status_code == 400:
            print("✓ User already exists")
        else:
            print(f"✗ Registration failed: {response.status_code} - {response.text[:100]}")
            # Don't raise - continue anyway, user might already exist
    
    def login(self):
        """Login and get JWT token."""
        print(f"Logging in as {self.customer_id}...")
        
        # ✅ Use correct field names: user_id (not username)
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={  # ✅ Use json= not data= for JSON body
                "user_id": self.customer_id,  # ✅ Correct field name
                "password": self.password
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            print("✓ Login successful")
            return True
        else:
            print(f"✗ Login failed: {response.status_code} - {response.text[:100]}")
            return False
    
    def ensure_wallet(self):
        """Ensure wallet exists with minimum balance."""
        self.register_user()
        
        if not self.login():
            print("✗ Cannot proceed without authentication")
            return False
        
        print(f"Ensuring wallet for {self.customer_id}...")
        
        response = requests.get(
            f"{self.base_url}/api/wallet/{self.customer_id}",
            headers=self.headers,
            timeout=10
        )
        
        if response.status_code == 200:
            balance = self._safe_json(response, "balance", 0)
            print(f"✓ Wallet balance: {balance}")
            if balance < 500:
                print("Topping up wallet...")
                self._credit_wallet(1000.0 - balance)
            return True
        elif response.status_code == 404:
            print("Creating wallet...")
            return self._credit_wallet(1000.0)
        else:
            print(f"✗ Wallet check failed: {response.status_code}")
            return False
    
    def _credit_wallet(self, amount):
        """Internal: Credit wallet."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/wallet/{self.customer_id}/credit",
                json={"amount": amount},
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 200:
                balance = self._safe_json(resp, "balance")
                print(f"✓ Credited {amount}, balance: {balance}")
                return True
        except Exception as e:
            print(f"✗ Credit error: {e}")
        return False
    
    def _debit_wallet(self, amount):
        """Internal: Debit wallet."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/wallet/{self.customer_id}/debit",
                json={"amount": amount},
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 200:
                balance = self._safe_json(resp, "balance")
                print(f"✓ Debited {amount}, balance: {balance}")
                return True
        except Exception as e:
            print(f"✗ Debit error: {e}")
        return False
    
    def _create_order(self, amount, currency="INR"):
        """Internal: Create order."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/orders",
                json={
                    "customer_id": self.customer_id,  # ✅ Must match logged-in user
                    "amount": amount,
                    "currency": currency
                },
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 201:
                print(f"✓ Order created: {amount} {currency}")
                return True
        except Exception as e:
            print(f"✗ Order error: {e}")
        return False
    
    def _get_wallet_balance(self):
        """Internal: Get wallet balance safely."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/wallet/{self.customer_id}",
                headers=self.headers,
                timeout=10
            )
            return self._safe_json(resp, "balance", 0.0)
        except:
            return 0.0
    
    def _get_orders_count(self):
        """Internal: Get orders count safely."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/orders?customer_id={self.customer_id}",
                headers=self.headers,
                timeout=10
            )
            if resp.status_code == 200:
                return len(resp.json())
        except:
            pass
        return 0
    
    def mixed(self):
        """Mixed operations scenario."""
        print("\n=== Running mixed scenario ===")
        
        if not self.ensure_wallet():
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
                self._credit_wallet(amount)
            elif op_type == "debit":
                print(f"\nDebiting {amount}...")
                self._debit_wallet(amount)
            elif op_type == "order":
                print(f"\nCreating order for {amount}...")
                self._create_order(amount)
            
            time.sleep(0.2)
        
        print("\n=== Final state ===")
        # ✅ Safe access - no KeyError
        balance = self._get_wallet_balance()
        print(f"Wallet balance: {balance}")
        
        order_count = self._get_orders_count()
        print(f"Total orders: {order_count}")
    
    def orders_retry(self):
        """Idempotency test scenario."""
        print("\n=== Running orders_retry scenario ===")
        
        if not self.ensure_wallet():
            return
        
        idempotency_key = f"retry-{int(time.time())}"
        payload = {
            "customer_id": self.customer_id,
            "amount": 499.99,
            "currency": "INR",
            "idempotency_key": idempotency_key
        }
        
        print(f"Attempt 1 with key: {idempotency_key}")
        resp1 = requests.post(
            f"{self.base_url}/api/orders",
            json=payload,
            headers=self.headers,
            timeout=2.0
        )
        print(f"Response 1: {resp1.status_code}")
        
        print(f"Attempt 2 (same key)...")
        resp2 = requests.post(
            f"{self.base_url}/api/orders",
            json=payload,
            headers=self.headers,
            timeout=5.0
        )
        print(f"Response 2: {resp2.status_code}")
        
        time.sleep(1)
        
        # Count orders with this idempotency key
        orders = requests.get(
            f"{self.base_url}/api/orders?customer_id={self.customer_id}",
            headers=self.headers,
            timeout=10
        ).json() if requests.get(
            f"{self.base_url}/api/orders?customer_id={self.customer_id}",
            headers=self.headers,
            timeout=10
        ).status_code == 200 else []
        
        matching = [o for o in orders if o.get("idempotency_key") == idempotency_key]
        print(f"Orders with key '{idempotency_key}': {len(matching)} (expected: 1)")


def main():
    parser = argparse.ArgumentParser(description="Payment API Test Scenarios")
    
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
    
    runner = ScenarioRunner(
        base_url=args.base_url,
        customer_id=args.customer_id,
        password=args.password
    )
    
    # Run selected scenario
    if args.scenario == "mixed":
        runner.mixed()
    elif args.scenario == "orders_retry":
        runner.orders_retry()
    else:
        print(f"Unknown scenario: {args.scenario}")
        sys.exit(1)


if __name__ == "__main__":
    main()