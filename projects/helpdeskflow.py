"""Persistent tickets with an enforced lifecycle and transactional audit trail."""
import argparse
from .common import database, nonempty, rows, run

SCHEMA = '''
CREATE TABLE IF NOT EXISTS tickets (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, priority TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'open', assignee TEXT);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, ticket_id INTEGER REFERENCES tickets(id),
 action TEXT NOT NULL, detail TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
'''
TRANSITIONS = {'open': {'in_progress'}, 'in_progress': {'resolved'},
               'resolved': {'closed', 'in_progress'}, 'closed': set()}


def create(path, title, priority='normal'):
    title = nonempty(title)
    if priority not in {'low', 'normal', 'high'}:
        raise ValueError('Priority must be low, normal, or high')
    with database(path, SCHEMA) as db:
        ident = db.execute('INSERT INTO tickets(title, priority) VALUES (?, ?)',
                           (title, priority)).lastrowid
        db.execute('INSERT INTO events(ticket_id,action,detail) VALUES (?,?,?)',
                   (ident, 'created', title))
        return {'id': ident, 'status': 'open'}


def change(path, ident, action, value):
    value = nonempty(value)
    with database(path, SCHEMA) as db:
        ticket = db.execute('SELECT * FROM tickets WHERE id=?', (ident,)).fetchone()
        if ticket is None:
            raise ValueError('Ticket not found')
        if action == 'status':
            if value not in TRANSITIONS[ticket['status']]:
                raise ValueError('Invalid status transition')
            db.execute('UPDATE tickets SET status=? WHERE id=?', (value, ident))
        elif action == 'assign':
            db.execute('UPDATE tickets SET assignee=? WHERE id=?', (value, ident))
        elif action != 'comment':
            raise ValueError('Unknown action')
        db.execute('INSERT INTO events(ticket_id,action,detail) VALUES (?,?,?)',
                   (ident, action, value))
        return dict(db.execute('SELECT * FROM tickets WHERE id=?', (ident,)).fetchone())


def inspect(path, ident=None):
    with database(path, SCHEMA) as db:
        if ident is None:
            return rows(db.execute('SELECT * FROM tickets ORDER BY id'))
        return rows(db.execute('SELECT * FROM events WHERE ticket_id=? ORDER BY id', (ident,)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='helpdeskflow.db')
    commands = parser.add_subparsers(dest='command', required=True)
    new = commands.add_parser('create'); new.add_argument('title')
    new.add_argument('--priority', choices=['low', 'normal', 'high'], default='normal')
    for action in ['status', 'assign', 'comment']:
        command = commands.add_parser(action)
        command.add_argument('id', type=int); command.add_argument('value')
    commands.add_parser('list')
    history = commands.add_parser('history'); history.add_argument('id', type=int)
    args = parser.parse_args()
    if args.command == 'create':
        run(lambda: create(args.db, args.title, args.priority))
    elif args.command in {'list', 'history'}:
        run(lambda: inspect(args.db, getattr(args, 'id', None)))
    else:
        run(lambda: change(args.db, args.id, args.command, args.value))


if __name__ == '__main__':
    main()
