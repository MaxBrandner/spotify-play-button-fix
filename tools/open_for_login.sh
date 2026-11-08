#!/usr/bin/env bash
# Open the test profile without automation, for the one-time manual login.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$root/test-profile"
cp "$root/tools/user.js" "$root/test-profile/user.js"
exec firefox --new-instance --profile "$root/test-profile" https://open.spotify.com
