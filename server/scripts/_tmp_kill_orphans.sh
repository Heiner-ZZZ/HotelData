#!/bin/sh
# Kill orphan pytest processes inside the server container (test DB flock).
for p in /proc/[0-9]*/cmdline; do
  pid=$(echo "$p" | cut -d/ -f3)
  cmd=$(tr '\0' ' ' < "$p" 2>/dev/null)
  case "$cmd" in
    *pytest*)
      echo "PID $pid: $(echo "$cmd" | head -c 80)"
      kill -9 "$pid" 2>/dev/null && echo "  -> killed -9"
      ;;
  esac
done
sleep 2
echo "--- SURVIVORS ---"
found=0
for p in /proc/[0-9]*/cmdline; do
  pid=$(echo "$p" | cut -d/ -f3)
  cmd=$(tr '\0' ' ' < "$p" 2>/dev/null)
  case "$cmd" in
    *pytest*) echo "AUN VIVO PID $pid"; found=1 ;;
  esac
done
[ "$found" = "0" ] && echo "ninguno"
echo "fin"
