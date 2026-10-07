"""Detect rolling-window authentication failures in JSON Lines input."""
import argparse
import json
from collections import defaultdict, deque
from .common import nonempty, timestamp, run


def analyze(lines, threshold=3, window=300):
    if threshold < 1 or window < 1:
        raise ValueError('Threshold and window must be positive')
    events, seen = [], {}
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            for field in ['id', 'timestamp', 'user', 'source', 'outcome']:
                nonempty(event[field])
            if event['outcome'] not in {'success', 'failure'}:
                raise ValueError('Outcome must be success or failure')
            moment = timestamp(event['timestamp'])
            if event['id'] in seen:
                if seen[event['id']] != event:
                    raise ValueError('Conflicting duplicate event ID')
                continue
            seen[event['id']] = event
            events.append((moment, event))
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f'Invalid log line {number}: {error}') from error
    queues, alerts = defaultdict(deque), []
    for moment, event in sorted(events, key=lambda item: item[0]):
        if event['outcome'] != 'failure':
            continue
        queue = queues[(event['user'], event['source'])]
        while queue and (moment - queue[0][0]).total_seconds() > window:
            queue.popleft()
        queue.append((moment, event['id']))
        if len(queue) >= threshold:
            alerts.append({'user': event['user'], 'source': event['source'],
                           'timestamp': moment.isoformat(), 'count': len(queue),
                           'evidence': [item[1] for item in queue]})
    return alerts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file'); parser.add_argument('--threshold', type=int, default=3)
    parser.add_argument('--window', type=int, default=300, help='Inclusive window in seconds')
    args = parser.parse_args()
    def execute():
        with open(args.file, encoding='utf-8') as source:
            return analyze(source, args.threshold, args.window)
    run(execute)


if __name__ == '__main__':
    main()
