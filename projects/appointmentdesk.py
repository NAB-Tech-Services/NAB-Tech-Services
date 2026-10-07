"""Timezone-aware bookings with serialized overlap protection."""
import argparse
from .common import database, nonempty, timestamp, rows, run

SCHEMA = '''
CREATE TABLE IF NOT EXISTS bookings (
 id INTEGER PRIMARY KEY, provider TEXT NOT NULL, client TEXT NOT NULL,
 start REAL NOT NULL, end REAL NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0,
 CHECK(end > start));
'''


def book(path, provider, client, start, end, ident=None):
    provider, client = nonempty(provider), nonempty(client)
    start, end = timestamp(start).timestamp(), timestamp(end).timestamp()
    if end <= start:
        raise ValueError('End must be after start')
    with database(path, SCHEMA) as db:
        if ident is not None and not db.execute(
                'SELECT id FROM bookings WHERE id=? AND cancelled=0', (ident,)).fetchone():
            raise ValueError('Active booking not found')
        conflict = db.execute('SELECT id FROM bookings WHERE provider=? AND cancelled=0 '
                              'AND start < ? AND end > ? AND id != ?',
                              (provider, end, start, ident or -1)).fetchone()
        if conflict:
            raise ValueError('Appointment overlaps an existing booking')
        if ident is None:
            ident = db.execute('INSERT INTO bookings(provider,client,start,end) VALUES (?,?,?,?)',
                               (provider, client, start, end)).lastrowid
        else:
            db.execute('UPDATE bookings SET provider=?,client=?,start=?,end=? WHERE id=?',
                       (provider, client, start, end, ident))
        return {'id': ident, 'booked': True}


def cancel(path, ident):
    with database(path, SCHEMA) as db:
        if db.execute('UPDATE bookings SET cancelled=1 WHERE id=? AND cancelled=0',
                      (ident,)).rowcount != 1:
            raise ValueError('Active booking not found')
    return {'id': ident, 'cancelled': True}


def inspect(path):
    from datetime import datetime, timezone
    with database(path, SCHEMA) as db:
        result = rows(db.execute('SELECT * FROM bookings ORDER BY start'))
    for row in result:
        for field in ['start', 'end']:
            row[field] = datetime.fromtimestamp(row[field], timezone.utc).isoformat()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='appointmentdesk.db')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['book', 'reschedule']:
        command = commands.add_parser(name)
        if name == 'reschedule':
            command.add_argument('id', type=int)
        for field in ['provider', 'client', 'start', 'end']:
            command.add_argument(field)
    command = commands.add_parser('cancel'); command.add_argument('id', type=int)
    commands.add_parser('list')
    args = parser.parse_args()
    if args.command == 'list':
        run(lambda: inspect(args.db))
    elif args.command == 'cancel':
        run(lambda: cancel(args.db, args.id))
    else:
        run(lambda: book(args.db, args.provider, args.client, args.start, args.end,
                         getattr(args, 'id', None)))


if __name__ == '__main__':
    main()
