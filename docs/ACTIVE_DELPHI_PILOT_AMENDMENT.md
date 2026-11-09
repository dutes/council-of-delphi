# Post-run note on the active Delphi pilot ownership gate

Date: 2026-09-25

The frozen engineering pilot specified that “no provider owns a given link
position more than five times.” That threshold is mathematically impossible in
a 30-question design with three providers: each of the three link positions
must be assigned 30 times, so exact provider-by-position balance is 10
assignments per provider. The intended value of five applies instead to each
of the six complete provider permutations, because 30 / 6 = 5.

This error was identified only after the frozen analysis printed `FAIL` for the
ownership gate. The frozen protocol, configuration, implementation hash, raw
database, and original analysis output have not been changed. The result is
reported as follows:

- formal frozen overall gate result: **FAIL**, caused by an impossible balance
  threshold;
- intended rotation check: **PASS**—each of the six permutations occurred five
  times and each provider occupied each link position ten times;
- all substantive feasibility gates: **PASS**.

The confirmatory protocol will state both balance requirements explicitly and
use values appropriate to its sample size. This note does not change or add an
accuracy outcome.

