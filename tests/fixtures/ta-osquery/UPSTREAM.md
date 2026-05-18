# TA-OSquery upstream

- **Source:** Splunkbase — `ta-osquery_104.tgz` (TA-OSqueryv1)
- **Author:** Rod Soto
- **Version:** 1.0.4
- **License:** Apache-2.0 (see `LICENSE.txt` in this directory)
- **Tarball SHA-256:** see commit history if reproducibility matters

This fixture is the unmodified Splunkbase release. Brief uses it to exercise the scanner against real-world add-on metadata (`props.conf`, `transforms.conf`, `eventtypes.conf`, `tags.conf`). It deliberately has no `savedsearches.conf` — that's typical for a TA, and the absence is itself a useful test signal.
