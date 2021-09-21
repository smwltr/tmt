#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    opt="-i $run --scratch provision prepare -vvv finish"
    rlPhaseStartTest "Run on all guests"
        rlRun -s "tmt run $opt plan -n all"
        rlAssertGrep "4 preparations applied" $rlRun_LOG
        rlRun "grep 'script: echo' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "4" lines
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Run on a single guest"
        rlRun -s "tmt run $opt plan -n name"
        rlAssertGrep "1 preparation applied" $rlRun_LOG
        rlAssertgrep "on: server-one" $rlRun_LOG
        rlRun "grep 'script: echo' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "1" lines
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Run on all guests with a role"
        rlRun -s "tmt run $opt plan -n role"
        rlAssertGrep "2 preparations applied" $rlRun_LOG
        rlAssertgrep "on: server" $rlRun_LOG
        rlRun "grep 'script: echo' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "2" lines
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Combined case"
        rlRun -s "tmt run $opt plan -n combined"
        # 1 ran on all (4 guests) + 1 ran on server role (2 guests) + 1 ran
        # on single guest (1 guest) = 7 preparations
        rlAssertGrep "7 preparations applied" $rlRun_LOG
        rlRun "grep 'All' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "4" lines
        rlRun "grep 'Server' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "2" lines
        rlRun "grep 'Client one' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "1" lines
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm lines"
        rlRun "popd"
        rlRun "rm -r $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
