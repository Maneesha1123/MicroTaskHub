#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <docker-username> [version]" >&2
  exit 1
fi

DOCKER_USERNAME="$1"
VERSION=1.0.0

services=(
  "frontend"
  "user-service"
  "task-service"
)

for service in "${services[@]}"; do
  image="${DOCKER_USERNAME}/microtaskhub-${service}:${VERSION}"
  context="services/${service}"
  echo "Building ${image} from ${context}..."
  docker build -t "${image}" "${context}"
  echo "Pushing ${image}..."
  docker push "${image}"
  echo "DONE: ${image}"
done
