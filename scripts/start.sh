#!/usr/bin/env bash
# Detect NVIDIA GPU and run docker compose with the GPU override if available.
# Usage: ./scripts/start.sh [up|down|logs|pull] [--with-app] (defaults to 'up -d')

set -euo pipefail
# Parse positional and optional flag --with-app
with_app=0
# Collect args
args=()
for arg in "$@"; do
  case "$arg" in
    --with-app)
      with_app=1
      ;;
    *)
      args+=("$arg")
      ;;
  esac
done

cmd=${args[0]:-up}
if [ "$cmd" = "up" ]; then
  extra_args="-d"
else
  extra_args=""
fi

# Respect START_APP env var
if [ "${START_APP:-}" != "" ]; then
  with_app=1
fi

# Compose base files
base_compose="-f docker-compose.yml"
gpu_compose="-f docker-compose.gpu.yml"

# Profile arg if enabling app
profile_arg=()
if [ "$with_app" -eq 1 ]; then
  profile_arg=(--profile ai-file-organizer)
fi

# Function to check for nvidia-smi or devices
has_nvidia() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    return 0
  fi
  # Check for /dev/nvidia* devices
  if [ -e /dev/nvidiactl ] || [ -e /dev/nvidia0 ]; then
    return 0
  fi
  return 1
}

run_compose() {
  # Use array expansion for profile arg
  docker compose $base_compose "$@"
}

if has_nvidia; then
  if [ -f docker-compose.gpu.yml ]; then
    echo "NVIDIA GPU detected — launching with GPU compose override"
    docker compose $base_compose $gpu_compose "${profile_arg[@]}" $cmd $extra_args
  else
    echo "NVIDIA GPU detected but docker-compose.gpu.yml not found — launching without GPU override"
    docker compose $base_compose "${profile_arg[@]}" $cmd $extra_args
  fi
else
  echo "No NVIDIA GPU detected — launching without GPU override"
  docker compose $base_compose "${profile_arg[@]}" $cmd $extra_args
fi
