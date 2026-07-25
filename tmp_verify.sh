#!/usr/bin/env bash
# Verify the housekeeping charges endpoints behave correctly against the user's two reported bugs.

set +e
cd infra 2>/dev/null || cd ../infra 2>/dev/null

COOKIES=/tmp/hk2/cookies.txt
mkdir -p /tmp/hk2

# Login
curl -sS -c $COOKIES -b $COOKIES -w 'login=%{http_code}\n' --max-time 10 \
  -X POST http://localhost:4200/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"superadmin","password":"Admin12345*"}' \
  -o /dev/null

echo "=== 1. Detail endpoint with VALID ObjectId (matches bug-report URL base) ==="
curl -sS -c $COOKIES -b $COOKIES -w '\nHTTP=%{http_code}\n' --max-time 10 \
  'http://localhost:4200/api/housekeeping/charges/6a4b12bf276feb05280e2dd4' \
  -o /tmp/hk2/d1.json
head -c 800 /tmp/hk2/d1.json
echo ""
echo ""

echo "=== 2. Detail endpoint with MALFORMED id from user report: 6a4b12bf...:1 ==="
curl -sS -c $COOKIES -b $COOKIES -w '\nHTTP=%{http_code}\n' --max-time 10 \
  'http://localhost:4200/api/housekeeping/charges/6a4b12bf276feb05280e2dd4:1' \
  -o /tmp/hk2/d2.json
head -c 400 /tmp/hk2/d2.json
echo ""
echo ""

echo "=== 3. Detail endpoint with UNKNOWN valid-format ObjectId ==="
curl -sS -c $COOKIES -b $COOKIES -w '\nHTTP=%{http_code}\n' --max-time 10 \
  'http://localhost:4200/api/housekeeping/charges/aaaaaaaaaaaaaaaaaaaaaaaa' \
  -o /tmp/hk2/d3.json
head -c 400 /tmp/hk2/d3.json
echo ""
echo ""

echo "=== 4. Detail endpoint with totally bogus string ==="
curl -sS -c $COOKIES -b $COOKIES -w '\nHTTP=%{http_code}\n' --max-time 10 \
  'http://localhost:4200/api/housekeeping/charges/not-an-objectid' \
  -o /tmp/hk2/d4.json
head -c 400 /tmp/hk2/d4.json
echo ""
