"""Print inspectable metrics for real, standard-library-only synthetic training."""
import json
from training import Config, report, synthetic_rows, train


def main():
    rows = synthetic_rows()
    config = Config()
    # Only an in-memory demonstration; production checkpoints require durable storage.
    early = train(rows, config, stop_after_epoch=8)
    final = train(rows, config, checkpoint=json.loads(json.dumps(early)))
    print(json.dumps(report(rows, config, final), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
