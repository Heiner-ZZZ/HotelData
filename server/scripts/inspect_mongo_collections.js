use("hoteldata_hub");
var cols = db.getCollectionNames().sort();
cols.forEach(function(c) {
  if (c.startsWith("fs.")) return;
  if (c === "audit_log" || c === "user_activity_logs" || c === "click_events" || c === "etl_executions" || c === "outbox") return;
  var doc = db[c].findOne();
  if (!doc) { print("*** " + c + ": EMPTY ***"); return; }
  print("\n========== " + c + " ==========");
  for (var key in doc) {
    var val = doc[key];
    var typeStr = typeof val;
    if (val === null) typeStr = "null";
    else if (typeof val === "object") {
      if (Array.isArray(val)) typeStr = "array[" + val.length + "]";
      else if (val._bsontype === "ObjectId") typeStr = "ObjectId";
      else if (val instanceof Date) typeStr = "Date";
      else continue;
    }
    var valDisp = "";
    if (typeStr === "string" && val.length < 150) valDisp = ' = "' + val.replace(/"/g, '\\"') + '"';
    else if (typeStr === "number") valDisp = " = " + val;
    else if (typeStr === "boolean") valDisp = " = " + val;
    else if (typeStr.startsWith("array") && val.length < 10) {
      valDisp = " = [";
      for (var a = 0; a < val.length && a < 5; a++) {
        if (a > 0) valDisp += ", ";
        var itemStr = JSON.stringify(val[a]);
        if (itemStr.length > 80) itemStr = itemStr.substring(0, 80) + "...";
        valDisp += itemStr;
      }
      valDisp += "]";
    }
    print(key + "|" + typeStr + "|" + valDisp);
  }
});
