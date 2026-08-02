#!/bin/sh
set -eu

config_file=/usr/share/nginx/html/runtime-config.js
license_key=${SYNCFUSION_LICENSE_KEY:-}
# Encode the value for a JavaScript double-quoted string. The license is
# runtime configuration, not source code; never interpolate it unescaped.
# License tokens must be printable; reject control characters rather than
# allowing an environment value to break the generated JavaScript.
case "$license_key" in
  *[![:print:]]*)
    printf '%s\n' 'SYNCFUSION_LICENSE_KEY contains unsupported control characters.' >&2
    exit 1
    ;;
esac
escaped_key=$(printf '%s' "$license_key" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
printf '%s\n' "window.__HOTELDATA_CONFIG__ = { syncfusionLicenseKey: \"$escaped_key\" };" > "$config_file"

exec nginx -g 'daemon off;'
