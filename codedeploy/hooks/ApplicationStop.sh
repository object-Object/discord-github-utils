#!/bin/bash
set -euox pipefail

cd /var/lib/codedeploy-apps/discord-github-utils

docker compose down
