print('=== ALL databases in replica set ===');
db.adminCommand({ listDatabases: 1, nameOnly: false }).databases.forEach(function (d) {
  print('  ' + d.name + '  sizeOnDisk=' + d.sizeOnDisk);
});
print('');
print('=== Try DB names app may actually use ===');
['hoteldata','hotel_data','hotel','hotels','pms','cms','main','app','dev'].forEach(function (dbname) {
  var s = db.getSiblingDB(dbname);
  var n = s.getCollectionNames().length;
  if (n > 0) {
    print('  HIT: ' + dbname + ' has ' + n + ' collections');
    s.getCollectionNames().sort().slice(0, 30).forEach(function (c) {
      print('    ' + c + ' count=' + s[c].countDocuments({}));
    });
  }
});
print('');
print('=== current effective db context ===');
print('  db.getName() = ' + db.getName());
