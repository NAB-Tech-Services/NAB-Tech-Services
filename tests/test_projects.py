import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from projects import helpdeskflow as tickets, assettrack as assets
from projects import appointmentdesk as bookings, logsignal as logs
from projects import uptimepulse as uptime, documentflow as pdf


class ProjectsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = str(self.root / 'test.db')

    def test_ticket_lifecycle_and_history(self):
        ident = tickets.create(self.db, 'Printer offline')['id']
        tickets.change(self.db, ident, 'assign', 'Demo Technician')
        tickets.change(self.db, ident, 'comment', 'Checked connection')
        for state in ['in_progress', 'resolved', 'closed']:
            tickets.change(self.db, ident, 'status', state)
        self.assertEqual(tickets.inspect(self.db)[0]['status'], 'closed')
        self.assertEqual(len(tickets.inspect(self.db, ident)), 6)

    def test_ticket_invalid_transition_rolls_back(self):
        ident = tickets.create(self.db, 'Test')['id']
        with self.assertRaises(ValueError):
            tickets.change(self.db, ident, 'status', 'closed')
        self.assertEqual(tickets.inspect(self.db)[0]['status'], 'open')
        self.assertEqual(len(tickets.inspect(self.db, ident)), 1)

    def test_asset_exclusive_assignment_and_history(self):
        assets.register(self.db, 'PC-01', 'Demo laptop')
        with self.assertRaises(sqlite3.IntegrityError):
            assets.register(self.db, 'PC-01', 'Duplicate')
        assets.checkout(self.db, 'PC-01', 'Alex')
        with self.assertRaises(sqlite3.IntegrityError):
            assets.checkout(self.db, 'PC-01', 'Jordan')
        assets.checkin(self.db, 'PC-01')
        assets.checkout(self.db, 'PC-01', 'Jordan')
        self.assertEqual(len(assets.inspect(self.db, True)), 2)
        self.assertEqual(assets.inspect(self.db)[0]['person'], 'Jordan')

    def test_asset_unknown_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            assets.checkout(self.db, 'missing', 'Alex')
        with self.assertRaises(ValueError):
            assets.checkin(self.db, 'missing')

    def reserve(self, start='2026-11-01T01:00:00-05:00', end='2026-11-01T01:30:00-05:00', ident=None):
        return bookings.book(self.db, 'Demo Provider', 'Demo Client', start, end, ident)

    def test_booking_offsets_adjacent_and_cancel(self):
        ident = self.reserve()['id']
        with self.assertRaises(ValueError):
            self.reserve('2026-11-01T06:00:00Z', '2026-11-01T06:30:00Z')
        self.reserve('2026-11-01T06:30:00Z', '2026-11-01T07:00:00Z')
        # Repeated wall-clock hour with a different DST offset is a different instant.
        self.reserve('2026-11-01T01:00:00-06:00', '2026-11-01T01:30:00-06:00')
        bookings.cancel(self.db, ident)
        self.reserve()
        self.assertEqual(len(bookings.inspect(self.db)), 4)

    def test_booking_naive_and_reversed_times(self):
        with self.assertRaises(ValueError):
            self.reserve('2026-11-01T01:00:00', '2026-11-01T01:30:00')
        with self.assertRaises(ValueError):
            self.reserve('2026-11-01T07:00:00Z', '2026-11-01T06:00:00Z')

    def test_reschedule_conflict_preserves_original(self):
        ident = self.reserve()['id']
        self.reserve('2026-11-01T07:00:00Z', '2026-11-01T08:00:00Z')
        with self.assertRaises(ValueError):
            self.reserve('2026-11-01T07:00:00Z', '2026-11-01T08:00:00Z', ident)
        self.assertEqual(bookings.inspect(self.db)[0]['start'], '2026-11-01T06:00:00+00:00')

    def test_concurrent_booking_only_one_wins(self):
        bookings.inspect(self.db)
        barrier = threading.Barrier(2)
        def attempt(_):
            barrier.wait()
            try:
                self.reserve()
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(attempt, range(2)))
        self.assertEqual(sorted(result), [False, True])
        self.assertEqual(len(bookings.inspect(self.db)), 1)

    def log(self, ident, minute, second=0, outcome='failure'):
        return json.dumps({'id': ident, 'timestamp': f'2026-01-01T00:{minute:02}:{second:02}Z',
                           'user': 'demo', 'source': '192.0.2.1', 'outcome': outcome})

    def test_log_window_boundary_dedup_and_sort(self):
        values = [self.log('c', 5), self.log('a', 0), self.log('b', 2), self.log('a', 0)]
        result = logs.analyze(values)
        self.assertEqual(result[0]['evidence'], ['a', 'b', 'c'])
        self.assertEqual(logs.analyze([self.log('a', 0), self.log('b', 2), self.log('c', 5, 1)]), [])

    def test_log_success_and_bad_input(self):
        self.assertEqual(logs.analyze([self.log('a', 0, outcome='success')], threshold=1), [])
        for values in [['{}'], ['not-json'], [self.log('a', 0), self.log('a', 1)]]:
            with self.assertRaises(ValueError):
                logs.analyze(values)

    def test_uptime_incident_threshold_recovery_and_percentage(self):
        result = {'url': 'https://example.test', 'healthy': False, 'status': 503,
                  'latency_ms': 1, 'error': 'Unavailable'}
        uptime.record(self.db, result)
        self.assertEqual(uptime.report(self.db)['incidents'], [])
        uptime.record(self.db, result); uptime.record(self.db, result)
        self.assertEqual(len(uptime.report(self.db)['incidents']), 1)
        uptime.record(self.db, dict(result, healthy=True, status=200, error=None))
        report = uptime.report(self.db)
        self.assertIsNotNone(report['incidents'][0]['closed_at'])
        self.assertEqual(report['availability'][0]['sample_success_percent'], 25)

    def test_uptime_real_http_errors_redirect_and_timeout(self):
        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self):
                if self.path == '/slow':
                    time.sleep(0.1)
                status = {'/ok': 200, '/redirect': 302, '/bad': 503}.get(self.path, 200)
                self.send_response(status)
                if status == 302:
                    self.send_header('Location', '/ok')
                self.end_headers()
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}'
            self.assertTrue(uptime.probe(url + '/ok')['healthy'])
            self.assertEqual(uptime.probe(url + '/redirect')['status'], 302)
            self.assertFalse(uptime.probe(url + '/bad')['healthy'])
            self.assertFalse(uptime.probe(url + '/slow', timeout=0.01)['healthy'])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_uptime_invalid_targets(self):
        for url in ['file:///etc/passwd', 'https://user:password@example.test', 'https://']:
            with self.assertRaises(ValueError):
                uptime.probe(url)

    def make_pdf(self, name, widths=(100, 200), encrypted=False):
        path = self.root / name
        writer = PdfWriter()
        for width in widths:
            writer.add_blank_page(width=width, height=300)
        if encrypted:
            writer.encrypt('test-password')
        writer.write(path); writer.close()
        return path

    def test_pdf_merge_extract_rotate_preserves_inputs(self):
        source = self.make_pdf('source.pdf'); original = source.read_bytes()
        second = self.make_pdf('second.pdf', (400,))
        output = self.root / 'merged.pdf'
        pdf.process([source, second], output)
        self.assertEqual([float(p.mediabox.width) for p in PdfReader(output).pages], [100, 200, 400])
        extracted = self.root / 'extracted.pdf'
        pdf.process([output], extracted, pages='3,1', rotation=90)
        pages = PdfReader(extracted).pages
        self.assertEqual([float(p.mediabox.width) for p in pages], [400, 100])
        self.assertEqual([p.rotation for p in pages], [90, 90])
        self.assertEqual(source.read_bytes(), original)

    def test_pdf_invalid_ranges_and_no_overwrite(self):
        source = self.make_pdf('source.pdf')
        with self.assertRaises(ValueError):
            pdf.process([source], source)
        output = self.root / 'bad.pdf'
        for pages in ['0', '3', '2-1', '1-2-3']:
            with self.assertRaises(ValueError):
                pdf.process([source], output, pages=pages)
        self.assertFalse(output.exists())

    def test_pdf_encrypted_and_malformed_rejected(self):
        encrypted = self.make_pdf('encrypted.pdf', encrypted=True)
        broken = self.root / 'broken.pdf'; broken.write_text('not a pdf')
        for source in [encrypted, broken]:
            with self.assertRaises(ValueError):
                pdf.process([source], self.root / 'output.pdf')
        self.assertFalse((self.root / 'output.pdf').exists())

    def test_all_cli_entrypoints(self):
        for name in ['helpdeskflow', 'assettrack', 'appointmentdesk', 'logsignal', 'uptimepulse', 'documentflow']:
            result = subprocess.run([sys.executable, '-m', 'projects.' + name, '--help'], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, '-m', 'projects.helpdeskflow', '--db', self.db,
                                 'create', 'Demo request'], capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['id'], 1)
        invalid = subprocess.run([sys.executable, '-m', 'projects.helpdeskflow', '--db', self.db,
                                  'status', '1', 'closed'], capture_output=True, text=True)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn('Invalid status transition', invalid.stderr)


if __name__ == '__main__':
    unittest.main()
