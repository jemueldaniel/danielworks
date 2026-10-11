"""A synthetic worker crash and recovery, using a real disposable SQLite file."""
import json
from pathlib import Path
import tempfile

from jobs import JobQueue, LeaseLost


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'demo.sqlite'
        with JobQueue(path) as queue:
            queue.submit('team-demo', 'count-items', {'items': [2, 4, 6]})
            old = queue.claim('team-demo', now=0, lease_ticks=2)
        # The first worker has disappeared. A second connection observes expiry.
        with JobQueue(path) as queue:
            current = queue.claim('team-demo', now=2, lease_ticks=5)
            if current is None or old is None:
                raise RuntimeError('expected a claimed job')
            stale_rejected = False
            try:
                queue.complete(old, {'count': 0}, now=3)
            except LeaseLost:
                stale_rejected = True
            queue.complete(current, {'count': len(current.payload['items'])}, now=3)
            row = queue.inspect('team-demo', 'count-items')
            print(json.dumps({'status': row['state'], 'attempts': row['attempts'],
                              'stale_worker_rejected': stale_rejected, 'result': row['result']}, sort_keys=True))


if __name__ == '__main__':
    main()
