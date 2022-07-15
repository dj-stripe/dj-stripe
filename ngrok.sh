#!/usr/bin/env bash

# Add ngrok config token
ngrok config add-authtoken 293TSkGoe5leBi9xiEvwQNqoYS3_3ET5ZBjGQheeMx57mnbjM

# expose a local https server
# and provide custom host header for istio and other services
# ngrok http https://dev.com --host-header="dev.com"
ngrok http http://localhost:8000
