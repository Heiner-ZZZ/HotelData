print('==== 1. reception_shifts counts ====');
print('   total = ' + db.reception_shifts.countDocuments({}));
print('   last 24h = ' + db.reception_shifts.countDocuments({start_time:{$gte:new Date(Date.now()-24*3600*1000)}}));
print('');
print('==== 2. audit_log counts ====');
print('   total = ' + db.audit_log.countDocuments({}));
print('   reception_shifts rows (24h) = ' + db.audit_log.countDocuments({entity_type:'reception_shifts', created_at:{$gte:new Date(Date.now()-24*3600*1000)}}));
print('   shift_schedule (audit of bypass) = ' + db.audit_log.countDocuments({entity_type:'shift_schedule'}));
print('');
print('==== 3. last 5 reception_shifts docs ====');
db.reception_shifts.find().sort({_id:-1}).limit(5).forEach(function(d){
  print('   id=' + d._id + ' t=' + d.shift_type + ' by=' + d.opened_by + ' status=' + d.status + ' start=' + (d.start_time instanceof Date ? d.start_time.toISOString() : String(d.start_time)));
});
print('');
print('==== 4. last 10 audit_log rows (reception_shifts OR shift_schedule only) ====');
db.audit_log.find({$or:[{entity_type:'reception_shifts'},{entity_type:'shift_schedule'}]}).sort({_id:-1}).limit(10).forEach(function(d){
  print('   et=' + d.entity_type + ' act=' + d.action + ' by=' + (d.changed_by||'') + ' eid=' + (d.entity_id||'') + ' ts=' + (d.created_at instanceof Date ? d.created_at.toISOString() : String(d.created_at)) + ' sum=' + String(d.summary||'').substring(0,180));
});
