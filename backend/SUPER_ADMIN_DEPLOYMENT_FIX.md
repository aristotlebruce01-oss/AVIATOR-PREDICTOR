# Super Admin login fix (Render)

This update adds a safe, one-time startup initializer for the configured Super Admin and pins bcrypt to a Passlib-compatible version.

## What it does

- Reads `SUPER_ADMIN_NAME`, `SUPER_ADMIN_EMAIL`, and `SUPER_ADMIN_PASSWORD` from the backend environment.
- Creates a Super Admin only if the configured email is not already in use and no Super Admin already exists.
- Gives the account a referral code and sets its commission rate to `0`.
- Does **not** change an existing user's role or password, and does not delete or reset users, payments, payment options, receipts, or the database.
- If an account already exists, logs a message explaining why initialization was skipped.

## Render steps

1. Open the Render dashboard and select the `aviator-predictor-backend-ri36` service.
2. Open **Environment** and add/check these variables. Enter your actual password privately in Render; do not put it in source code or share it in chat.
   - `SUPER_ADMIN_NAME` = your full name
   - `SUPER_ADMIN_EMAIL` = the email you will use to sign in
   - `SUPER_ADMIN_PASSWORD` = a strong password of at least 6 characters (8+ recommended)
3. Keep the existing `DATABASE_URL` and `JWT_SECRET` unchanged. Do not delete or replace the production database.
4. Commit and push the updated backend files to the connected GitHub branch, or deploy the updated source through your existing process.
5. In Render logs, look for one of these messages:
   - `Super Admin account created successfully...`
   - `Configured Super Admin account already exists...`
   - `Super Admin initialization stopped...`
   - `Super Admin initialization skipped...`
6. Sign in with the configured **email and password**. This API's current login accepts email or phone; it does not support username login.

## If login still fails

- If logs say the account already exists, this initializer deliberately does not reset its password. Use the existing account's correct password or arrange a deliberate, separately reviewed password recovery.
- If logs say a different Super Admin exists, do not delete database rows. Confirm which existing account should remain the Super Admin before changing anything.
- A successful deployment alone does not prove login works; confirm the startup log and test the login form.
