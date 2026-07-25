// ============================================================
// Post-implementation forensic for reception_shift audit rows
// Run: docker compose exec -T mongo mongosh --quiet --port 27018 hoteldata /tmp/diag.js
// ============================================================

print('==== 1. all collections whose name matches /audit/ ====');
db.getCollectionNames()
  .filter(function (c) { return /audit/i.test(c); })
  .forEach(function (c) {
    print('   ' + c + '  count=' + db[c].countDocuments({}));
  });

print('');
print('==== 2. last 20 audit_log rows (any age, sorted by _id desc) ====');
var last20 = db.audit_log.find().sort({ _id: -1 }).limit(20).toArray();
print('   total rows in response: ' + last20.length);
last20.forEach(function (d) {
  var ts = d.created_at instanceof Date ? d.created_at.toISOString() : String(d.created_at || '');
  print(
    '   et=' + d.entity_type +
    '  act=' + d.action +
    '  by=' + (d.changed_by || '') +
    '  eid=' + (d.entity_id || '') +
    '  ts=' + ts +
    '  sum=' + String(d.summary || '').substring(0, 160)
  );
});

print('');
print('==== 3. reception_shift audit rows in last 24h ====');
var recent = db.audit_log.find({
  entity_type: 'reception_shifts',
  created_at: { $gte: new Date(Date.now() - 24 * 3600 * 1000) }
}).sort({ _id: -1 }).limit(20).toArray();
print('   reception_shifts rows (24h): ' + recent.length);
recent.forEach(function (d) {
  print(
    '   act=' + d.action +
    '  eid=' + (d.entity_id || '') +
    '  by=' + (d.changed_by || '') +
    '  ts=' + (d.created_at instanceof Date ? d.created_at.toISOString() : '')
  );
});

print('');
print('==== 4. last 5 reception_shifts in collection ====');
db.reception_shifts.find().sort({ _id: -1 }).limit(5).forEach(function (d) {
  var st = d.start_time instanceof Date ? d.start_time.toISOString() : String(d.start_time || '');
  print(
    '   id=' + d._id +
    '  t=' + (d.shift_type || '') +
    '  opened_by=' + (d.opened_by || '') +
    '  opened_by_id=' + (d.opened_by_id || '') +
    '  status=' + (d.status || '') +
    '  start=' + st
  );
});

print('');
print('==== DONE ====');
