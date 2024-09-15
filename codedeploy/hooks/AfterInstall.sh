#!/bin/bash
set -euox pipefail

cd /var/lib/codedeploy-apps/discord-github-utils

echo -e "\nDEPLOYMENT__TIMESTAMP=\"$(date +%s)\"" >> .env
