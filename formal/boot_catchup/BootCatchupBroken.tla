---------------------------- MODULE BootCatchupBroken ----------------------------
\* Broken boot: marks booted but does not catch up (pre-catch-up reboot).
EXTENDS Naturals, Integers, FiniteSets

CONSTANTS MaxDay, Lookback
ASSUME MaxDay \in Nat /\ Lookback \in Nat /\ Lookback > 0

Unreleased == 0 - 1

VARIABLES day, releaseDay, searched, booted

Title == {"t0", "t1"}

TypeOK ==
  /\ day \in 0 .. MaxDay
  /\ releaseDay \in [Title -> (Unreleased .. MaxDay)]
  /\ searched \subseteq Title
  /\ booted \in BOOLEAN

Init ==
  /\ day = 0
  /\ releaseDay = [t \in Title |-> Unreleased]
  /\ searched = {}
  /\ booted = FALSE

Release(t) ==
  /\ releaseDay[t] = Unreleased
  /\ releaseDay' = [releaseDay EXCEPT ![t] = day]
  /\ UNCHANGED <<day, searched, booted>>

Tick ==
  /\ day < MaxDay
  /\ day' = day + 1
  /\ UNCHANGED <<releaseDay, searched, booted>>

Rss ==
  /\ searched' = searched \union { t \in Title : releaseDay[t] = day }
  /\ UNCHANGED <<day, releaseDay, booted>>

InLookback(t) ==
  /\ releaseDay[t] # Unreleased
  /\ day - releaseDay[t] <= Lookback
  /\ releaseDay[t] <= day

Boot ==
  /\ booted' = TRUE
  /\ UNCHANGED <<day, releaseDay, searched>>

Next ==
  \/ \E t \in Title : Release(t)
  \/ Tick
  \/ Rss
  \/ Boot

Spec == Init /\ [][Next]_<<day, releaseDay, searched, booted>>

BootCoversLookback ==
  booted => (\A t \in Title : InLookback(t) => t \in searched)

=============================================================================
