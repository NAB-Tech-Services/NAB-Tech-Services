"""Equipment inventory with exclusive checkout and assignment history."""
import argparse
from .common import database, nonempty, rows, run

SCHEMA = '''
CREATE TABLE IF NOT EXISTS assets (tag TEXT PRIMARY KEY, description TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assignments (
 id INTEGER PRIMARY KEY, tag TEXT NOT NULL REFERENCES assets(tag), person TEXT NOT NULL,
 checked_out TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, checked_in TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_assignment ON assignments(tag)
 WHERE checked_in IS NULL;
'''


def register(path, tag, description):
    with database(path, SCHEMA) as db:
        db.execute('INSERT INTO assets VALUES (?,?)', (nonempty(tag), nonempty(description)))
    return {'tag': tag, 'registered': True}


def checkout(path, tag, person):
    with database(path, SCHEMA) as db:
        db.execute('INSERT INTO assignments(tag,person) VALUES (?,?)',
                   (nonempty(tag), nonempty(person)))
    return {'tag': tag, 'assigned_to': person}


def checkin(path, tag):
    with database(path, SCHEMA) as db:
        result = db.execute('UPDATE assignments SET checked_in=CURRENT_TIMESTAMP '
                            'WHERE tag=? AND checked_in IS NULL', (tag,))
        if result.rowcount != 1:
            raise ValueError('Asset has no active assignment')
    return {'tag': tag, 'checked_in': True}


def inspect(path, history=False):
    with database(path, SCHEMA) as db:
        if history:
            return rows(db.execute('SELECT * FROM assignments ORDER BY id'))
        return rows(db.execute('SELECT a.*, s.person FROM assets a LEFT JOIN assignments s '
                               'ON a.tag=s.tag AND s.checked_in IS NULL ORDER BY a.tag'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='assettrack.db')
    commands = parser.add_subparsers(dest='command', required=True)
    new = commands.add_parser('register'); new.add_argument('tag'); new.add_argument('description')
    out = commands.add_parser('checkout'); out.add_argument('tag'); out.add_argument('person')
    back = commands.add_parser('checkin'); back.add_argument('tag')
    commands.add_parser('list'); commands.add_parser('history')
    args = parser.parse_args()
    actions = {'register': lambda: register(args.db, args.tag, args.description),
               'checkout': lambda: checkout(args.db, args.tag, args.person),
               'checkin': lambda: checkin(args.db, args.tag),
               'list': lambda: inspect(args.db), 'history': lambda: inspect(args.db, True)}
    run(actions[args.command])


if __name__ == '__main__':
    main()
