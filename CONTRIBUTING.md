# Contributing

Changes should preserve the matched nature of the baseline and AES-CTR
implementations: same board, clock, UART, FIFO, pinout, and timing constraints,
with AES-CTR as the intended design difference.

Before proposing a change, run the smallest affected test and, for RTL or
shared build changes, run:

~~~bash
make check
git diff --check
~~~

Keep private GPS traces, experiment contexts, keys, nonce registries, and
generated build outputs out of commits. When adding a result, identify the
method and evidence type; do not label simulation, Quartus analysis, and
physical capture as interchangeable.

The submitted manuscript is archived under the paper/ directory. Changes to
its source should be reviewed against the archived PDF and the selected metrics
snapshot.
