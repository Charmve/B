#!/bin/bash

# shellcheck disable=all
# -*- sh -*- (Bash only)

# qbuild commands
: ${QBUILD:=qbuild}
: ${QBUILD_IGNORED_COMMAND_REGEX:="__none__"}

# Usage: _qbuild__expand_package_name <workspace> <displacement> <current-word>
#                                    <label-type>
#
# Expands directories, but explores all roots of
# BAZEL_COMPLETION_PACKAGE_PATH, not just $(pwd).  When a directory is
# a qbuild package, the completion offers "pkg:" so you can expand
# inside the package.
# Sets $COMPREPLY array to result.
_qbuild__expand_package_name() {
  local workspace=$1 displacement=$2 current=$3 type=${4:-} root dir index
  for root in $(_qbuild__package_path "$workspace" "$displacement"); do
    found=0
    for dir in $(compgen -d $root$current); do
      [ -L "$dir" ] && continue                   # skip symlinks (e.g. qbuild-bin)
      [[ "$dir" =~ ^(.*/)?\.[^/]*$ ]] && continue # skip dotted dir (e.g. .git)
      found=1
      echo "${dir#$root}/"
      if [ -f $dir/BUILD.bazel -o -f $dir/BUILD ]; then
        if [ "${type}" = "label-package" ]; then
          echo "${dir#$root} "
        else
          echo "${dir#$root}:"
        fi
      fi
    done
    [ $found -gt 0 ] && break # Stop searching package path upon first match.
  done
}

# Usage: _qbuild__expand_target_pattern <workspace> <displacement>
#                                      <word> <label-syntax>
#
# Expands "word" to match target patterns, using the current workspace
# and displacement from it.  "command" is used to filter rules.
# Sets $COMPREPLY array to result.
_qbuild__expand_target_pattern() {
  local workspace=$1 displacement=$2 current=$3 label_syntax=$4
  case "$current" in
    //*:*) # Expand rule names within package, no displacement.
      if [ "${label_syntax}" = "label-package" ]; then
        compgen -S " " -W "BUILD" "$(echo current | cut -f ':' -d2)"
      else
        _qbuild__expand_rules_in_package "$workspace" "" "$current" "$label_syntax"
      fi
      ;;
    *:*) # Expand rule names within package, displaced.
      if [ "${label_syntax}" = "label-package" ]; then
        compgen -S " " -W "BUILD" "$(echo current | cut -f ':' -d2)"
      else
        _qbuild__expand_rules_in_package \
          "$workspace" "$displacement" "$current" "$label_syntax"
      fi
      ;;
    //*) # Expand filenames using package-path, no displacement
      _qbuild__expand_package_name "$workspace" "" "$current" "$label_syntax"
      ;;
    *) # Expand filenames using package-path, displaced.
      if [ -n "$current" ]; then
        _qbuild__expand_package_name "$workspace" "$displacement" "$current" "$label_syntax"
      fi
      ;;
  esac
}

_qbuild__get_command() {
  for word in "${COMP_WORDS[@]:1:COMP_CWORD-1}"; do
    if echo "$QBUILD_COMMAND_LIST" | "grep" -wsq -e "$word"; then
      echo $word
      break
    fi
  done
}

# Usage: _qbuild__options_for <command>
#
# Prints the set of options for a given Bazel command, e.g. "build".
_qbuild__options_for() {
  local options
  if [[ "${QBUILD_COMMAND_LIST}" =~ ^(.* )?$1( .*)?$ ]]; then
    # assumes option names only use ASCII characters
    local option_name=$(echo $1 | tr a-z A-Z | tr "-" "_")
    eval "echo \${QBUILD_COMMAND_${option_name}_FLAGS}" | tr " " "\n"
  fi
}

# Usage: _qbuild__expansion_for <command>
#
# Prints the completion pattern for a given Bazel command, e.g. "build".
_qbuild__expansion_for() {
  local options
  if [[ "${QBUILD_COMMAND_LIST}" =~ ^(.* )?$1( .*)?$ ]]; then
    # assumes option names only use ASCII characters
    local option_name=$(echo $1 | tr a-z A-Z | tr "-" "_")
    eval "echo \${QBUILD_COMMAND_${option_name}_ARGUMENT}"
  fi
}

_qbuild__is_after_doubledash() {
  for word in "${COMP_WORDS[@]:1:COMP_CWORD-1}"; do
    if [[ "$word" == "--" ]]; then
      return 0
    fi
  done
  return 1
}

# Usage: _qbuild__complete_pattern <workspace> <displacement> <current>
#                                 <type>
#
# Expand a word according to a type. The currently supported types are:
#  - {a,b,c}: an enum that can take value a, b or c
#  - label: a label of any kind
#  - label-bin: a label to a runnable rule (basically to a _binary rule)
#  - label-test: a label to a test rule
#  - info-key: an info key as listed by `qbuild help info-keys`
#  - command: the name of a command
#  - path: a file path
#  - combinaison of previous type using | as separator
_qbuild__complete_pattern() {
  local workspace=$1 displacement=$2 current=$3 types=$4
  for type in $(echo $types | tr "|" "\n"); do
    case "$type" in
      label*)
        _qbuild__expand_target_pattern "$workspace" "$displacement" \
          "$current" "$type"
        ;;
      info-key)
        compgen -S " " -W "${BAZEL_INFO_KEYS}" -- "$current"
        ;;
      "command")
        local commands=$(echo "${BAZEL_COMMAND_LIST}" \
          | tr " " "\n" | "grep" -v "^${BAZEL_IGNORED_COMMAND_REGEX}$")
        compgen -S " " -W "${commands}" -- "$current"
        ;;
      path)
        for file in $(compgen -f -- "$current"); do
          if [[ -d "$file" ]]; then
            echo "$file/"
          else
            echo "$file "
          fi
        done
        ;;
      *)
        compgen -S " " -W "$type" -- "$current"
        ;;
    esac
  done
}

# Usage: _qbuild__expand_options <workspace> <displacement> <current-word>
#                               <options>
#
# Expands options, making sure that if current-word contains an equals sign,
# it is handled appropriately.
_qbuild__expand_options() {
  local workspace="$1" displacement="$2" cur="$3" options="$4"
  if [[ $cur =~ = ]]; then
    # also expands special labels
    current=$(echo "$cur" | cut -f2 -d=)
    _qbuild__complete_pattern "$workspace" "$displacement" "$current" \
      "$(compgen -W "$options" -- "$cur" | cut -f2 -d=)" \
      | sort -u
  else
    compgen -W "$(echo "$options" | sed 's|=.*$|=|')" -- "$cur" \
      | sed 's|\([^=]\)$|\1 |'
  fi
}

# Usage: _qbuild__abspath <file>
#
#
# Returns the absolute path to a file
_qbuild__abspath() {
  echo "$(
    cd "$(dirname "$1")"
    pwd
  )/$(basename "$1")"
}

_qbuild__to_compreply() {
  local replies="$1"
  COMPREPLY=()
  # Trick to preserve whitespaces
  while IFS="" read -r reply; do
    COMPREPLY+=("${reply}")
  done < <(echo "${replies}")
  # Null may be set despite there being no completions
  if [ ${#COMPREPLY[@]} -eq 1 ] && [ -z ${COMPREPLY[0]} ]; then
    COMPREPLY=()
  fi
}

_qbuild__complete() {
  _qbuild__to_compreply "$(_qbuild__complete_stdout)"
}

_qbuild__complete_stdout() {

  # Determine command: "" (startup-options) or one of $QBUILD_COMMAND_LIST.
  command="$(_qbuild__get_command)"
  echo "$command"

  if _qbuild__is_after_doubledash && [[ "$command" == "run" ]]; then
    echo "debug- $command" == "run"
    #_qbuild__complete_pattern "$workspace" "$displacement" "${cur#*=}" "path"
  else
    case "$command" in
      "") # Expand startup-options or commands
        local commands=$(echo "${QBUILD_COMMAND_LIST}" \
          | tr " " "\n" | "grep" -v "^${QBUILD_IGNORED_COMMAND_REGEX}$")
        _qbuild__expand_options "$workspace" "$displacement" "$cur" \
          "${commands}\
            ${QBUILD_STARTUP_OPTIONS}"
        ;;

      *)
        case "$cur" in
          #   --config=*) # Expand options:
          #     _qbuild__expand_config "$workspace" "$command" "${cur#"--config="}"
          #     ;;
          -*) # Expand options:
            _qbuild__expand_options "$workspace" "$displacement" "$cur" \
              "$(_qbuild__options_for $command)"
            ;;
          *) # Expand target pattern
            expansion_pattern="$(_qbuild__expansion_for $command)"
            NON_QUOTE_REGEX="^[\"']"
            echo $expansion_pattern $NON_QUOTE_REGEX
            # if [[ $command = query && $cur =~ $NON_QUOTE_REGEX ]]; then
            #   : # Ideally we would expand query expressions---it's not
            #   # that hard, conceptually---but readline is just too
            #   # damn complex when it comes to quotation.  Instead,
            #   # for query, we just expand target patterns, unless
            #   # the first char is a quote.
            # elif [ -n "$expansion_pattern" ]; then
            #   _qbuild__complete_pattern \
            #     "$workspace" "$displacement" "$cur" "$expansion_pattern"
            # fi
            ;;
        esac
        ;;
    esac
  fi
}

# default completion for qbuild
complete -F _qbuild__complete -o nospace "${QBUILD}"

QBUILD_COMMAND_LIST="analyze-profile aquery build canonicalize-flags clean config coverage cquery dump fetch help info license mobile-install print_action query run shutdown sync test version"

QBUILD_STARTUP_OPTIONS="
--init
--build
--connect
--deploy
--run
--update
--format
--pull
--test
--unittest
--benchmark
--coverage
--sonarqube
--version
--help
"
