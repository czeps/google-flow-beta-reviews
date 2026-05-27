"""Run all three feature-analysis stages end to end.

If out/features_taxonomy.json already exists, stage 1 is skipped (so you can
edit the taxonomy and rerun classification + aggregation without regenerating).

Use --restart-classify to drop prior classification progress.
"""

from __future__ import annotations

import argparse

from loguru import logger

from analyzer import aggregate, classify, taxonomy
from analyzer.common import TAXONOMY_PATH


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="sonnet (default), haiku, or full model id")
    ap.add_argument("--force-taxonomy", action="store_true", help="regenerate taxonomy even if it exists")
    ap.add_argument("--restart-classify", action="store_true", help="drop prior classification rows")
    ap.add_argument("--limit", type=int, default=0, help="classify only N reviews (testing)")
    args = ap.parse_args()

    if args.force_taxonomy or not TAXONOMY_PATH.exists():
        logger.info("=== stage 1: taxonomy ===")
        tax_args = ["--model", args.model] if args.model else []
        if args.force_taxonomy:
            tax_args.append("--force")
        taxonomy.main(tax_args)
        logger.warning(
            "Taxonomy generated. Inspect/edit out/features_taxonomy.json, "
            "then rerun this script (without --force-taxonomy) to classify & aggregate."
        )
        return
    else:
        logger.info(f"=== stage 1: taxonomy already exists at {TAXONOMY_PATH}; skipping ===")

    logger.info("=== stage 2: classify ===")
    cls_args = []
    if args.model:
        cls_args += ["--model", args.model]
    if args.restart_classify:
        cls_args.append("--restart")
    if args.limit:
        cls_args += ["--limit", str(args.limit)]
    classify.main(cls_args)

    logger.info("=== stage 3: aggregate ===")
    aggregate.main()
    logger.success("done -- see out/features.csv")


if __name__ == "__main__":
    main()
