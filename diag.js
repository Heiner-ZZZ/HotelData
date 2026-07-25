print('=== ALL audit-related collections ===');
db.getCollectionNames().filter(function(c){return /audit/i.test(c)}).forEach(function(c){
  print('  ' + c + ' count=' + db[c].countDocuments({}));
});
print('');
print('=== Last 20 audit_log entries by insertion order (_id desc) ===');
db.audit_log.find().sort({_id:-1}).limit(20).forEach(function(d){
  print('  et=' + d.entity_type + ' act=' + d.action + ' by=' + d.changed_by + ' eid=' + (d.entity_id||''));
});
print('');
print('=== Last 5 reception_shifts inserted ===');
db.reception_shifts.find().sort({_id:-1}).limit(5).forEach(function(d){
  print('  id=' + d._id + ' t=' + d.shift_type + ' opened_by=' + (d.opened_by||'NULL') + ' status=' + d.status);
});
