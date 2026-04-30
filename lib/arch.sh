#!/bin/bash
# Architecture and OS detection. Source after lib/common.sh.
#
# After sourcing:
#   $OS_KIND  = "darwin" | "linux"
#   $ARCH     = "x86_64" | "aarch64" | ""
#   $ARCH_ALT = upstream-style architecture used by some asset names ("amd64" | "arm64" | "")

[[ -n "${_ZCONFIG_ARCH_LOADED:-}" ]] && return 0
_ZCONFIG_ARCH_LOADED=1

case "$(uname)" in
    Darwin) OS_KIND="darwin" ;;
    Linux)  OS_KIND="linux" ;;
    *)      OS_KIND="" ;;
esac
export OS_KIND

case "$(uname -m)" in
    x86_64)        ARCH="x86_64";  ARCH_ALT="amd64" ;;
    aarch64|arm64) ARCH="aarch64"; ARCH_ALT="arm64" ;;
    *)             ARCH="";        ARCH_ALT="" ;;
esac
export ARCH ARCH_ALT
