#!/usr/bin/env bash
set -euo pipefail

npm run test:api
npm run build
npm run build:chat
