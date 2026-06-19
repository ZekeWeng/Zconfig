"""Shell completion scripts emitted by ``zconfig completion <shell>``.

Static templates — no engine state needed. Tool-name completion is dynamic:
the scripts shell back to ``zconfig list --json`` (fast, no probing) and extract
names with python3, which is always present since the CLI itself needs it.

Install:
  bash:  echo 'source <(zconfig completion bash)' >> ~/.bashrc
  zsh:   zconfig completion zsh > "${fpath[1]}/_zconfig"   # or source it in ~/.zshrc
"""

from __future__ import annotations

from .commands import command_names, tool_arg_command_names

_BASH = """\
# zconfig bash completion. Install: source <(zconfig completion bash)
_zconfig_tools() {
    zconfig list --json 2>/dev/null \\
        | python3 -c 'import sys,json; print(" ".join(t["name"] for t in json.load(sys.stdin)))' 2>/dev/null
}
_zconfig() {
    local cur prev sub i
    cur="${COMP_WORDS[COMP_CWORD]}"
    local cmds="%(commands)s"
    local global="--manifest --lock --log-file --version --help"
    sub=""
    for ((i=1; i<COMP_CWORD; i++)); do
        case "${COMP_WORDS[i]}" in
            -*) ;;
            *) sub="${COMP_WORDS[i]}"; break ;;
        esac
    done
    if [[ -z "$sub" ]]; then
        mapfile -t COMPREPLY < <(compgen -W "$cmds $global" -- "$cur")
        return
    fi
    case "$sub" in
        %(tool_arg)s)
            mapfile -t COMPREPLY < <(compgen -W "$(_zconfig_tools)" -- "$cur") ;;
        config)
            mapfile -t COMPREPLY < <(compgen -W "list get set unset default_tags default_platform" -- "$cur") ;;
        completion)
            mapfile -t COMPREPLY < <(compgen -W "bash zsh" -- "$cur") ;;
        *)
            mapfile -t COMPREPLY < <(compgen -W "--tags --yes --dry-run --json --help" -- "$cur") ;;
    esac
}
complete -F _zconfig zconfig
"""

_ZSH = """\
#compdef zconfig
# zconfig zsh completion. Install: zconfig completion zsh > "${fpath[1]}/_zconfig"
_zconfig() {
    local -a cmds
    cmds=(%(commands)s)
    if (( CURRENT == 2 )); then
        _describe 'command' cmds
        return
    fi
    case "${words[2]}" in
        %(tool_arg_zsh)s)
            local -a tools
            tools=(${(f)"$(zconfig list --json 2>/dev/null | python3 -c 'import sys,json;[print(t["name"]) for t in json.load(sys.stdin)]' 2>/dev/null)"})
            _describe 'tool' tools ;;
        config) _values 'arg' list get set unset default_tags default_platform ;;
        completion) _values 'shell' bash zsh ;;
        *) _values 'flag' --tags --yes --dry-run --json --help ;;
    esac
}
_zconfig "$@"
"""


def completion_script(shell: str) -> str | None:
    tool_args = "|".join(tool_arg_command_names())
    fields = {
        "commands": " ".join(command_names()),
        "tool_arg": tool_args,
        "tool_arg_zsh": tool_args,
    }
    if shell == "bash":
        return _BASH % fields
    if shell == "zsh":
        return _ZSH % fields
    return None
