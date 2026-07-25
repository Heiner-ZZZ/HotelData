print('=== ALL collections in hoteldata DB ===');
db.getCollectionNames().sort().forEach(function (c) {
  print('  ' + c + '  count=' + db[c].countDocuments({}));
});
print('');
print('=== Likely shift-related collections (last 3 docs each) ===');
['reception_shifts','reception_shift','shifts','shifts_open','cash_shifts','audit_log','system_audit_log','audit_actions','actions_log'].forEach(function (c) {
  if (db.getCollectionNames().indexOf(c) !== -1) {
    print('  --- ' + c + ' ---');
    var last3 = db[c].find().sort({_id:-1}).limit(3).toArray();
    last3.forEach(function (d) {
      var ts = d.created_at instanceof Date ? d.created_at.toISOString() : (d.start_time instanceof Date ? d.start_time.toISOString() : String(d._id));
      var keys = Object.keys(d).slice(0, 12).join(',');
      print('    id=' + d._id + ' keys=[' + keys + '] ts=' + ts);
    });
  } else {
    print('  [missing] ' + c);
  }
});
