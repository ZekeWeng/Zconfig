#!/bin/bash
# Bootstrap entrypoint for orchestrators and standalone installer runs.
# Source this file once; it loads every other lib in the right order.
#
# Usage from an orchestrator:
#   source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"
#
# Sourcing is idempotent — each lib has its own loaded-guard.

: "${ZCONFIG_DIR:=$HOME/.zconfig}"

# shellcheck source=common.sh
source "$ZCONFIG_DIR/lib/common.sh"
# shellcheck source=env.sh
source "$ZCONFIG_DIR/lib/env.sh"
# shellcheck source=verify.sh
source "$ZCONFIG_DIR/lib/verify.sh"
# shellcheck source=arch.sh
source "$ZCONFIG_DIR/lib/arch.sh"
# shellcheck source=pkg.sh
source "$ZCONFIG_DIR/lib/pkg.sh"
