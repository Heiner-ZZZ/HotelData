#!/usr/bin/env bash
# Inspect .additional_charges shape + booking FK state after the FK ObjectId migration.
# Single .sh file so we avoid heredoc escape issues.

set +e

cd infra 2>/dev/null || cd ../infra 2>/dev/null

mkdir -p /tmp/hk
COOKIES=/tmp/hk/cookies.txt
mkdir -p /tmp/hk/m

# === A. Login (cookie jar) ===
echo "=== A. LOGIN ==="
curl -sS -c $COOKIES -b $COOKIES \
  -w 'login HTTP=%{http_code}\n' --max-time 10 \
  -X POST http://localhost:4200/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"superadmin","password":"Admin12345*"}' \
  -o /tmp/hk/login.json
echo "--- login.json ---"
head -c 600 /tmp/hk/login.json
echo ""
echo "--- cookies (first 400 bytes) ---"
head -c 400 $COOKIES
echo ""
echo ""

# === B. GET /api/housekeeping/charges via nginx :4200 =====
echo "=== B. GET /api/housekeeping/charges via Nginx :4200 ==="
curl -sS -c $COOKIES -b $COOKIES \
  -w 'HTTP=%{http_code}\n' --max-time 10 \
  'http://localhost:4200/api/housekeeping/charges?prop_id=1&page=1&page_size=3' \
  -o /tmp/hk/c.json
head -c 3000 /tmp/hk/c.json
echo ""
echo ""

# === C. GET /api/housekeeping/charges direct backend :8000 ===
echo "=== C. GET /api/housekeeping/charges direct backend :8000 ==="
curl -sS -c $COOKIES -b $COOKIES \
  -w 'HTTP=%{http_code}\n' --max-time 10 \
  'http://localhost:8000/api/housekeeping/charges?prop_id=1&page=1&page_size=3' \
  -o /tmp/hk/c2.json
head -c 3000 /tmp/hk/c2.json
echo ""
echo ""

# === D. List collections in hoteldata DB ===
cat > /tmp/hk/m/coll.js <<'EOF'
db.getCollectionNames().sort().forEach(function(c){print(c)});
EOF
echo "=== D. Collections in hoteldata DB ==="
docker compose exec -T mongo mongosh --quiet --port 27018 hoteldata /tmp/hk/m/coll.js 2>&1 | head -80
echo ""

# === E. additional_charges count + 2 raw docs ===
cat > /tmp/hk/m/ac.js <<'EOF'
print('count=' + db.additional_charges.countDocuments({}));
print('--- 2 sample docs (sorted by created_at desc) ---');
db.additional_charges.find().sort({created_at:-1}).limit(2).forEach(function(d){printjson(d)});
EOF
echo "=== E. additional_charges count + 2 sample docs ==="
docker compose exec -T mongo mongosh --quiet --port 27018 hoteldata /tmp/hk/m/ac.js 2>&1 | head -200
echo ""

# === F. booking-like collections ===
cat > /tmp/hk/m/bk.js <<'EOF'
db.getCollectionNames().sort().forEach(function(c){
  if (/book|reservation|reserve/i.test(c)) {
    print(c + ' count=' + db[c].countDocuments({}));
  }
});
EOF
echo "=== F. Booking-like collection counts ==="
docker compose exec -T mongo mongosh --quiet --port 27018 hoteldata /tmp/hk/m/bk.js 2>&1 | head -30
echo ""

# === G. Type counts for candidate FK fields on additional_charges ===
cat > /tmp/hk/m/tc.js <<'EOF'
print('--- additional_charges: type counts for candidate FK field names ---');
function t(n){var q={};q[n]={$type:'objectId'};print('  ac.'+n+' objId='+db.additional_charges.countDocuments(q));}
function s(n){var q={};q[n]={$type:'string'};print('  ac.'+n+' string='+db.additional_charges.countDocuments(q));}
function e(n){var q={};q[n]={$exists:true};print('  ac.'+n+' exists='+db.additional_charges.countDocuments(q));}
['booking_id','booking_id_fk','bookingId','booking_ref','bookingFk','bookings_fk'].forEach(function(n){t(n);s(n);e(n)});
print('total docs=' + db.additional_charges.countDocuments({}));
EOF
echo "=== G. Type counts for candidate FK fields ==="
docker compose exec -T mongo mongosh --quiet --port 27018 hoteldata /tmp/hk/m/tc.js 2>&1 | head -40
echo ""

# === H. Full field inventory on additional_charges ===
cat > /tmp/hk/m/inv.js <<'EOF'
var seen={};
db.additional_charges.find().forEach(function(d){
  Object.keys(d).forEach(function(k){seen[k]=1});
});
Object.keys(seen).sort().forEach(function(k){print(k)});
EOF
echo "=== H. additional_charges: full field inventory ==="
docker compose exec -T mongo mongosh --quiet --port 27018 hoteldata /tmp/hk/m/inv.js 2>&1 | head -40
echo ""
