Quick Overview
This is a FastAPI-based payment API with user management, order processing, and wallet operations
JWT authentication has been implemented for secure access control
Only the user profile routes are protected - orders and wallet endpoints remain public for now
Uses PostgreSQL with SQLAlchemy for database operations
Passwords are hashed using bcrypt via passlib for security
Authentication: What's Protected and What's Not
Protected routes (require JWT token in Authorization header):
GET /api/users/{user_id} - Get user details by ID
GET /api/users - List all users (with pagination)
Public routes (no authentication required):
POST /api/auth/register - Register a new user
POST /api/auth/login - Login and get JWT token
POST /api/users - Create user (alternative registration endpoint)
All /api/orders/* endpoints - Order creation and listing
All /api/wallet/* endpoints - Wallet credit, debit, and balance checks
Important note: Only the user profile routes have authentication enabled. If you want to protect order or wallet routes, you'll need to add Depends(get_current_user) to those endpoints manually.
What Was Updated From the Original Codebase
New files added:
app/auth.py - This is now a unified file containing both the JWT authentication dependency (get_current_user) and the auth endpoints (/register and /login). No separate dependencies file needed.
app/security.py - Handles password hashing using bcrypt via passlib, and JWT token creation/verification using python-jose.
Files that were updated:
app/models.py - Added hashed_password column to the User model for storing encrypted passwords. Fixed the is_active field to be a proper Boolean type instead of String.
app/schemas.py - Added new schemas for authentication: UserLogin for login requests, Token for login responses, and TokenData for internal token parsing. Also added an internal User schema that matches the database model for use in dependencies.
app/services.py - Added the authenticate_user() function that verifies credentials. Updated create_user() to hash passwords before saving to the database.
app/config.py - Added JWT configuration settings: SECRET_KEY, ALGORITHM, and ACCESS_TOKEN_EXPIRE_MINUTES.
app/main.py - Updated to include the new auth router with the /api prefix so endpoints are accessible at /api/auth/login and /api/auth/register.
app/routes_users.py - Added Depends(get_current_user) to the GET endpoints so they now require a valid JWT token. Also added authorization logic so users can only view their own profile data unless they're an admin.
