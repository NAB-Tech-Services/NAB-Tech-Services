"""Operator-controlled HTTP checks with persistent incident tracking."""
import argparse
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from .common import database, rows, run

SCHEMA = '''
CREATE TABLE IF NOT EXISTS checks (
 id INTEGER PRIMARY KEY, url TEXT NOT NULL, healthy INTEGER NOT NULL,
 status INTEGER, latency_ms REAL NOT NULL, error TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS incidents (
 id INTEGER PRIMARY KEY, url TEXT NOT NULL, opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 closed_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_incident ON incidents(url) WHERE closed_at IS NULL;
'''


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(url, timeout=5):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use an HTTP(S) URL without embedded credentials')
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Timeout must be positive and finite')
    started, status, error = time.monotonic(), None, None
    opener = urllib.request.build_opener(NoRedirect())
    try:
        # HEAD avoids downloading unbounded response bodies. Redirects are failures.
        with opener.open(urllib.request.Request(url, method='HEAD'), timeout=timeout) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status, error = exc.code, str(exc)
        exc.close()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        error = str(exc)
    return {'url': url, 'healthy': status is not None and 200 <= status < 300,
            'status': status, 'latency_ms': round((time.monotonic() - started) * 1000, 2),
            'error': error}


def record(path, result, threshold=2):
    if threshold < 1:
        raise ValueError('Threshold must be positive')
    with database(path, SCHEMA) as db:
        db.execute('INSERT INTO checks(url,healthy,status,latency_ms,error) VALUES (?,?,?,?,?)',
                   tuple(result[key] for key in ['url', 'healthy', 'status', 'latency_ms', 'error']))
        if result['healthy']:
            db.execute('UPDATE incidents SET closed_at=CURRENT_TIMESTAMP '
                       'WHERE url=? AND closed_at IS NULL', (result['url'],))
        else:
            recent = db.execute('SELECT healthy FROM checks WHERE url=? ORDER BY id DESC LIMIT ?',
                                (result['url'], threshold)).fetchall()
            if len(recent) == threshold and not any(row['healthy'] for row in recent):
                db.execute('INSERT INTO incidents(url) SELECT ? WHERE NOT EXISTS '
                           '(SELECT 1 FROM incidents WHERE url=? AND closed_at IS NULL)',
                           (result['url'], result['url']))
    return result


def report(path):
    with database(path, SCHEMA) as db:
        return {'checks': rows(db.execute('SELECT * FROM checks ORDER BY id DESC LIMIT 50')),
                'incidents': rows(db.execute('SELECT * FROM incidents ORDER BY id')),
                'availability': rows(db.execute('SELECT url, COUNT(*) AS samples, '
                                                'ROUND(100.0*AVG(healthy),2) AS sample_success_percent '
                                                'FROM checks GROUP BY url'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='uptimepulse.db')
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('check'); check.add_argument('url')
    check.add_argument('--timeout', type=float, default=5)
    check.add_argument('--threshold', type=int, default=2)
    check.add_argument('--count', type=int, default=1)
    check.add_argument('--interval', type=float, default=60)
    commands.add_parser('report')
    args = parser.parse_args()
    def execute():
        if args.command == 'report':
            return report(args.db)
        if args.count < 1 or args.threshold < 1 or not math.isfinite(args.interval) or args.interval < 0:
            raise ValueError('Positive count/threshold and a finite nonnegative interval required')
        results = []
        for index in range(args.count):
            if index:
                time.sleep(args.interval)
            results.append(record(args.db, probe(args.url, args.timeout), args.threshold))
        return results
    run(execute)


if __name__ == '__main__':
    main()
