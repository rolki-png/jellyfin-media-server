# PR-5 broken boot counterexample (TLC)

`BootCatchupBroken` (boot marks `booted` but does not search) violates `BootCoversLookback`:

1. Init
2. Release t1 on day 0
3. Tick to day 1
4. Release t0 on day 1
5. Boot with empty `searched`

That is the pre-catch-up reboot: titles aired around downtime stay unsearched because RSS only sees "today".
