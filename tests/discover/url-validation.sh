#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

# Make it easier to see what went wrong
export TMT_SHOW_TRACEBACK=1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Unsafe git url is rejected"
        plan="/plans/shell/unsafe-url"
        rlRun -s "tmt run -i $run discover plans -n $plan" 2 "discover with ext:: url must fail"
        rlAssertGrep "Remote helper transport is not allowed in git url 'ext::sh -c false'" $rlRun_LOG
        # Rejected by tmt itself, git must not be even started
        rlAssertNotGrep "Cloning into" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Archive with unsafe members is rejected"
        # Python's extraction filters are available since 3.12.4
        if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12, 4) else 1)'; then
            serve=$(mktemp -d)
            tree=$(mktemp -d)

            python3 - "$serve/bad.tar.gz" <<'PYEOF'
import io
import sys
import tarfile

with tarfile.open(sys.argv[1], 'w:gz') as tar:
    for name in ('innocent.txt', '../../../escape.txt'):
        info = tarfile.TarInfo(name)
        info.size = 0
        tar.addfile(info, io.BytesIO(b''))
PYEOF
            rlRun "test -s $serve/bad.tar.gz" 0 "Create an archive with a path traversal member"

            python3 -m http.server 18931 --directory "$serve" --bind 127.0.0.1 &>/dev/null &
            server_pid=$!
            rlRun "sleep 1"

            mkdir -p "$tree/.fmf"
            echo 1 > "$tree/.fmf/version"
            cat > "$tree/plan.fmf" <<'EOF'
summary: Bad archive
discover:
    how: shell
    url: http://127.0.0.1:18931/bad.tar.gz
    url-content-type: archive
    tests:
      - name: ping
        test: "true"
EOF

            rlRun "pushd $tree"
            rlRun -s "tmt run -i $tree/run discover" 1 "discover with unsafe archive must fail"
            rlRun "popd"
            rlAssertGrep "outside the destination" $rlRun_LOG
            # The escaping member must not be extracted anywhere
            rlAssertNotExists "$tree/run/plan/escape.txt"
            rlAssertNotExists "$tree/escape.txt"

            kill $server_pid
            rm -rf "$serve" "$tree"
        else
            rlLogInfo "Skipping: extraction filters require Python 3.12.4+"
        fi
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf $run"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
