#!/usr/bin/env bash
#
# sauti-selftest.sh — everything about the sauti CLI that can be checked
# without booting the real stack: argument parsing, exit codes, preflight
# messages, pidfile/lockfile handling, and the process-matching helpers.
#
# A shell script that lies is worse than no script, so this exists to keep
# scripts/sauti honest. It never starts a container and never touches the
# owner's real voice services: every port, state directory and app module is
# redirected at fake values first.
#
#   ./scripts/sauti-selftest.sh          run everything
#   ./scripts/sauti-selftest.sh -v       also print output of failing cases
#
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAUTI="$SELF_DIR/sauti"
VERBOSE=0
[[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]] && VERBOSE=1

[[ -x "$SAUTI" ]] || { echo "selftest: $SAUTI is missing or not executable" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Sandbox. Fake ports/app-modules so nothing here can find, adopt or kill the
# real TTS/ASR servers, and a throwaway state dir for pidfiles and locks.
# ---------------------------------------------------------------------------

TMP="$(mktemp -d "${TMPDIR:-/tmp}/sauti-selftest.XXXXXX")"
cleanup() {
  # One case lets compose run against a stub file; tidy up anything it made.
  # The project name is a throwaway, never the owner's real "sauti" project.
  if [[ -f "$TMP/deploy/docker-compose.yml" ]] && docker info >/dev/null 2>&1; then
    docker compose -p sauti-selftest -f "$TMP/deploy/docker-compose.yml" \
      down --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP"
}
trap cleanup EXIT

export SAUTI_STATE_DIR="$TMP/state"
export SAUTI_TTS_PORT=47893
export SAUTI_ASR_PORT=47892
export SAUTI_TTS_APP="selftest_never_real_tts:app"
export SAUTI_ASR_APP="selftest_never_real_asr:app"
export SAUTI_URL="http://sauti-selftest.invalid:47880"
export SAUTI_PROJECT="sauti-selftest"
export NO_COLOR=1
mkdir -p "$SAUTI_STATE_DIR/run" "$SAUTI_STATE_DIR/logs"

# ---------------------------------------------------------------------------
# Tiny assert harness
# ---------------------------------------------------------------------------

PASS=0; FAIL=0; SKIP=0
OUT=""; CODE=0

run() { OUT="$("$@" 2>&1)"; CODE=$?; return 0; }

pass() { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
skip() { SKIP=$((SKIP+1)); printf '  skip %s (%s)\n' "$1" "$2"; }
fail() {
  FAIL=$((FAIL+1))
  printf '  FAIL %s\n' "$1"
  printf '       %s\n' "$2"
  if (( VERBOSE )); then printf '%s\n' "$OUT" | sed 's/^/       | /'; fi
}

exits() { # exits <name> <expected-code> <cmd...>
  local name="$1" want="$2"; shift 2
  run "$@"
  [[ "$CODE" == "$want" ]] && pass "$name" || fail "$name" "expected exit $want, got $CODE"
}

# exits_saying <name> <expected-code> <substring> -- <cmd...>
exits_saying() {
  local name="$1" want="$2" needle="$3"; shift 3
  [[ "${1:-}" == "--" ]] && shift
  run "$@"
  if [[ "$CODE" != "$want" ]]; then
    fail "$name" "expected exit $want, got $CODE"
  elif [[ "$OUT" != *"$needle"* ]]; then
    fail "$name" "output did not mention: $needle"
  else
    pass "$name"
  fi
}

section() { printf '\n%s\n' "$1"; }

# ---------------------------------------------------------------------------

printf 'sauti selftest — %s\n' "$SAUTI"

section 'usage and dispatch'

exits_saying 'help exits 0 and shows usage'      0 'usage: sauti' -- "$SAUTI" help
exits_saying 'no args falls back to usage'       0 'usage: sauti' -- "$SAUTI"
exits_saying '--help is accepted'                0 'usage: sauti' -- "$SAUTI" --help
exits_saying '--version prints a version'        0 'sauti 1.'     -- "$SAUTI" --version
exits_saying 'unknown subcommand exits 2'        2 'unknown command: frobnicate' -- "$SAUTI" frobnicate
exits_saying 'unknown subcommand still shows usage' 2 'usage: sauti' -- "$SAUTI" frobnicate

# Usage on an unknown command must go to stderr, so `sauti foo | something`
# does not silently look like success.
OUT="$("$SAUTI" frobnicate 2>/dev/null)"; CODE=$?
if [[ "$CODE" == 2 && -z "$OUT" ]]; then
  pass 'unknown subcommand writes nothing to stdout'
else
  fail 'unknown subcommand writes nothing to stdout' "stdout was: ${OUT:-<empty>} (exit $CODE)"
fi

section 'degrades cleanly without a TTY'

OUT="$("$SAUTI" help | cat)"
if [[ "$OUT" == *$'\033'* ]]; then
  fail 'no ANSI escapes when piped' 'found escape sequences in piped output'
else
  pass 'no ANSI escapes when piped'
fi

section 'preflight: compose file'

export SAUTI_COMPOSE_FILE="$TMP/nope/docker-compose.yml"
export SAUTI_ENV_FILE="$TMP/nope/.env.docker"
export SAUTI_ENV_EXAMPLE="$TMP/nope/.env.docker.example"

exits_saying 'up on a missing compose file fails'       1 'compose file not found' -- "$SAUTI" up --no-voice
exits_saying '...and names the path it looked for'      1 "$TMP/nope/docker-compose.yml" -- "$SAUTI" up --no-voice
exits_saying '...and says how to point elsewhere'       1 'SAUTI_REPO' -- "$SAUTI" up --no-voice
exits_saying 'logs on a missing compose file fails'     1 'compose file not found' -- "$SAUTI" logs api
exits_saying 'rebuild on a missing compose file fails'  1 'compose file not found' -- "$SAUTI" rebuild

section 'preflight: env file'

mkdir -p "$TMP/deploy"
export SAUTI_COMPOSE_FILE="$TMP/deploy/docker-compose.yml"
export SAUTI_ENV_FILE="$TMP/deploy/.env.docker"
export SAUTI_ENV_EXAMPLE="$TMP/deploy/.env.docker.example"
printf 'services: {}\n' > "$SAUTI_COMPOSE_FILE"

# No example on disk: fall back to naming the example file.
exits_saying 'missing env file fails'                1 'env file not found' -- "$SAUTI" up --no-voice
exits_saying '...and points at .env.docker.example'  1 '.env.docker.example' -- "$SAUTI" up --no-voice

# Example present: hand over a copy/paste-able command.
printf 'EXAMPLE=1\n' > "$SAUTI_ENV_EXAMPLE"
exits_saying 'missing env file suggests cp from the example' 1 "cp '$SAUTI_ENV_EXAMPLE'" -- "$SAUTI" up --no-voice
rm -f "$SAUTI_ENV_EXAMPLE"

section 'option parsing'

exits_saying '--no-voice is a valid flag for up' 1 'env file not found'    -- "$SAUTI" up --no-voice
exits_saying 'a typo is rejected, not ignored'   1 'unknown option'        -- "$SAUTI" up --no-vioce
exits_saying '...and the typo is echoed back'    1 '--no-vioce'            -- "$SAUTI" up --no-vioce
exits_saying 'down takes no arguments'           1 "takes no arguments"    -- "$SAUTI" down now
exits_saying 'restart takes one service at most' 1 'at most one service'   -- "$SAUTI" restart api web
exits_saying 'restart rejects unknown services'  1 'unknown service: nope' -- "$SAUTI" restart nope
exits_saying 'rebuild rejects unknown services'  1 'unknown service: nope' -- "$SAUTI" rebuild nope
exits_saying 'logs rejects unknown services'     1 'unknown argument'      -- "$SAUTI" logs nope
exits_saying 'rebuild refuses host voice services' 1 'host service' -- "$SAUTI" rebuild tts
exits_saying '...and suggests restart instead'     1 'sauti restart tts'   -- "$SAUTI" rebuild tts

section 'reset refuses to destroy data by accident'

# No flag, no TTY: it must refuse, and must not reach Docker.
exits_saying 'reset without the flag refuses'   1 'refuses to run unattended' -- "$SAUTI" reset < /dev/null
exits_saying '...and spells out the real flag'  1 '--yes-really'              -- "$SAUTI" reset < /dev/null
exits_saying '...and warns what is lost'        1 'deletes the database volume' -- "$SAUTI" reset < /dev/null

# An interactive-looking prompt that gets the wrong answer must also refuse.
run "$SAUTI" reset <<< "yes"
if [[ "$CODE" != 0 ]]; then pass 'reset aborts on a wrong confirmation'
else fail 'reset aborts on a wrong confirmation' "exit was $CODE"; fi

# With the flag, it must get past the prompt (and then fail on env preflight,
# which proves the flag path is reached rather than silently prompting).
exits_saying 'reset --yes-really skips the prompt' 1 'env file not found' -- "$SAUTI" reset --yes-really
exits_saying 'reset rejects unknown options'       1 'unknown option'     -- "$SAUTI" reset --yes-maybe

section 'lockfile'

mkdir -p "$SAUTI_STATE_DIR/run"
exec 8>"$SAUTI_STATE_DIR/run/sauti.lock"
if flock -n 8; then
  exits_saying 'a second command refuses while the lock is held' \
    1 'another sauti command is already running' -- "$SAUTI" down
  exits_saying '...and names the lock file' \
    1 "$SAUTI_STATE_DIR/run/sauti.lock" -- "$SAUTI" down
  # Read-only commands must NOT need the lock — status has to work mid-boot.
  run "$SAUTI" status
  [[ "$CODE" == 0 ]] && pass 'status works while the lock is held' \
                     || fail 'status works while the lock is held' "exit $CODE"
  flock -u 8
else
  skip 'lockfile contention' 'could not take the lock'
fi
exec 8>&-

run "$SAUTI" down
[[ "$CODE" == 0 ]] && pass 'the lock is released again afterwards' \
                   || fail 'the lock is released again afterwards' "exit $CODE"

section 'pidfiles'

# A pidfile left behind by a crashed run must not be mistaken for a live
# service, and `down` must clean it up rather than leaving it to rot.
printf '999999' > "$SAUTI_STATE_DIR/run/tts.pid"
exits_saying 'a stale pidfile does not fake a running service' 0 'tts  !!  down' -- "$SAUTI" status
run "$SAUTI" down
if [[ -f "$SAUTI_STATE_DIR/run/tts.pid" ]]; then
  fail 'down removes a stale pidfile' 'tts.pid still exists'
else
  pass 'down removes a stale pidfile'
fi

# down must survive Docker being unreachable / the compose file being absent —
# the voice half still has to be stopped.
SAUTI_COMPOSE_FILE="$TMP/nope/docker-compose.yml" run "$SAUTI" down
[[ "$CODE" == 0 ]] && pass 'down still works with no compose file' \
                   || fail 'down still works with no compose file' "exit $CODE"

section 'health checks never trust a bare process'

# Fake ports, nothing listening: every health probe must be false.
(
  export SAUTI_SOURCE_ONLY=1
  # shellcheck source=/dev/null
  source "$SAUTI"
  health_tts && exit 10
  health_asr && exit 11
  health_app && exit 12
  exit 0
)
case $? in
  0)  pass 'health probes are false when nothing is listening';;
  10) fail 'health probes are false when nothing is listening' 'health_tts returned true';;
  11) fail 'health probes are false when nothing is listening' 'health_asr returned true';;
  12) fail 'health probes are false when nothing is listening' 'health_app returned true';;
  *)  fail 'health probes are false when nothing is listening' 'unexpected error sourcing sauti';;
esac

section 'process matching (the wrapper-vs-server bug)'

# Regression guard: adopting a running voice service used to pick up the shell
# that launched uvicorn instead of uvicorn itself, so `down` killed the wrapper
# and left the server holding the port.
sleep 300 &
real_pid=$!
# The trailing ':' matters: `bash -c 'sleep 300'` execs sleep and replaces
# itself, so it would not be a wrapper at all.
bash -c 'sleep 300; :' &
wrapper_pid=$!
sleep 0.3

(
  export SAUTI_SOURCE_ONLY=1
  # shellcheck source=/dev/null
  source "$SAUTI"
  proc_matches "$real_pid" "sleep 300"    || exit 10
  proc_matches "$wrapper_pid" "sleep 300" && exit 11
  proc_matches "$real_pid" "not-in-cmdline" && exit 12
  proc_matches 999999 "sleep"             && exit 13
  pid_alive "$real_pid"                   || exit 14
  pid_alive 999999                        && exit 15
  exit 0
)
case $? in
  0)  pass 'matches the server, rejects the shell wrapper';;
  10) fail 'matches the server, rejects the shell wrapper' 'real process not matched';;
  11) fail 'matches the server, rejects the shell wrapper' 'shell wrapper WAS matched (regression)';;
  12) fail 'matches the server, rejects the shell wrapper' 'matched an unrelated command line';;
  13) fail 'matches the server, rejects the shell wrapper' 'matched a dead pid';;
  14) fail 'matches the server, rejects the shell wrapper' 'pid_alive said a live pid is dead';;
  15) fail 'matches the server, rejects the shell wrapper' 'pid_alive said a dead pid is alive';;
  *)  fail 'matches the server, rejects the shell wrapper' 'unexpected error sourcing sauti';;
esac
kill "$real_pid" "$wrapper_pid" 2>/dev/null
wait "$real_pid" "$wrapper_pid" 2>/dev/null

section 'port detection'

if command -v python3 >/dev/null 2>&1; then
  python3 -c '
import socket, sys, time
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 47899)); s.listen(1)
print("ready", flush=True)
time.sleep(20)
' > "$TMP/binder.out" 2>&1 &
  binder_pid=$!
  for _ in $(seq 1 40); do grep -q ready "$TMP/binder.out" 2>/dev/null && break; sleep 0.1; done

  (
    export SAUTI_SOURCE_ONLY=1
    # shellcheck source=/dev/null
    source "$SAUTI"
    port_in_use 47899 || exit 10
    port_in_use 47898 && exit 11
    [[ "$(port_pid 47899)" == "$binder_pid" ]] || exit 12
    exit 0
  )
  case $? in
    0)  pass 'a busy port is detected, and attributed to the right pid';;
    10) fail 'a busy port is detected, and attributed to the right pid' 'listening port reported free';;
    11) fail 'a busy port is detected, and attributed to the right pid' 'free port reported busy';;
    12) fail 'a busy port is detected, and attributed to the right pid' 'wrong pid for the listener';;
    *)  fail 'a busy port is detected, and attributed to the right pid' 'unexpected error';;
  esac
  kill "$binder_pid" 2>/dev/null; wait "$binder_pid" 2>/dev/null
else
  skip 'port detection' 'python3 not available'
fi

section 'a busy voice port that is not ours is refused'

if command -v python3 >/dev/null 2>&1; then
  python3 -c '
import socket, time
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 47893)); s.listen(1)
print("ready", flush=True)
time.sleep(20)
' > "$TMP/binder2.out" 2>&1 &
  binder2_pid=$!
  for _ in $(seq 1 40); do grep -q ready "$TMP/binder2.out" 2>/dev/null && break; sleep 0.1; done

  # Port checks come after the file checks, so the env file has to exist for
  # `up` to get that far.
  printf 'SELFTEST=1\n' > "$SAUTI_ENV_FILE"

  # SAUTI_TTS_PORT is 47893. An impostor on it must stop `up` with a message
  # that says which port and how to move the service.
  exits_saying 'a stranger on the TTS port stops up' 1 "port 47893" -- "$SAUTI" up
  exits_saying '...and suggests a port override'     1 'SAUTI_TTS_PORT' -- "$SAUTI" up

  # ...while --no-voice walks straight past the voice ports. It then fails on
  # the stub compose file, which is fine — the point is where it did NOT stop.
  SAUTI_APP_TIMEOUT=2 run "$SAUTI" up --no-voice
  if [[ "$OUT" == *"Skipping voice services"* && "$OUT" != *"47893"* ]]; then
    pass '--no-voice walks past the busy voice port'
  else
    fail '--no-voice walks past the busy voice port' 'it still tripped on the voice port'
  fi

  rm -f "$SAUTI_ENV_FILE"
  kill "$binder2_pid" 2>/dev/null; wait "$binder2_pid" 2>/dev/null
else
  skip 'busy voice port' 'python3 not available'
fi

section 'logs'

exits_saying 'logs tts with no log file yet is a clear error' 1 'no log file yet for tts' -- "$SAUTI" logs tts
printf 'hello from the tts log\n' > "$SAUTI_STATE_DIR/logs/tts.log"
exits_saying 'logs tts tails the host log file' 0 'hello from the tts log' -- "$SAUTI" logs tts

# ---------------------------------------------------------------------------

printf '\n%d passed, %d failed, %d skipped\n' "$PASS" "$FAIL" "$SKIP"
(( FAIL == 0 )) || exit 1
printf 'selftest OK\n'
