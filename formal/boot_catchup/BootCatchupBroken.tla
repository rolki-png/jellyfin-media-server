---------------------------- MODULE BootCatchupBroken ----------------------------
\* Broken boot: records lastBootDay but does not catch up.
EXTENDS Naturals, Integers, FiniteSets

CONSTANTS MaxDay, Lookback
ASSUME MaxDay \in Nat /\ Lookback \in Nat /\ Lookback > 0

Unreleased == 0 - 1

VARIABLES day, releaseDay, searched, lastBootDay

Title == {"t0", "t1"}

TypeOK ==
  /\ day \in 0 .. MaxDay
  /\ releaseDay \in [Title -> (Unreleased .. MaxDay)]
  /\ searched \subseteq Title
  /\ lastBootDay \in (Unreleased .. MaxDay)

Init ==
  /\ day = 0
  /\ releaseDay = [t \in Title |-> Unreleased]
  /\ searched = {}
  /\ lastBootDay = Unreleased

Release(t) ==
  /\ releaseDay[t] = Unreleased
  /\ releaseDay' = [releaseDay EXCEPT ![t] = day]
  /\ UNCHANGED <<day, searched, lastBootDay>>

Tick ==
  /\ day < MaxDay
  /\ day' = day + 1
  /\ UNCHANGED <<releaseDay, searched, lastBootDay>>

Rss ==
  /\ searched' = searched \union { t \in Title : releaseDay[t] = day }
  /\ UNCHANGED <<day, releaseDay, lastBootDay>>

InLookback(t) ==
  /\ releaseDay[t] # Unreleased
  /\ day - releaseDay[t] <= Lookback
  /\ releaseDay[t] <= day

Boot ==
  /\ lastBootDay' = day
  /\ UNCHANGED <<day, releaseDay, searched>>

Next ==
  \/ \E t \in Title : Release(t)
  \/ Tick
  \/ Rss
  \/ Boot

Spec == Init /\ [][Next]_<<day, releaseDay, searched, lastBootDay>>

BootCoversLookback ==
  \A t \in Title :
    (lastBootDay # Unreleased
     /\ releaseDay[t] # Unreleased
     /\ releaseDay[t] < lastBootDay
     /\ lastBootDay - releaseDay[t] <= Lookback)
      => t \in searched

=============================================================================
