"""Merge, extract, rotate, and inspect local PDFs without replacing files."""
import argparse
import io
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError
from .common import run


def reader(path):
    try:
        result = PdfReader(path, strict=True)
        if result.is_encrypted:
            raise ValueError('Encrypted PDFs are not supported')
        return result
    except (PyPdfError, EOFError) as error:
        raise ValueError(f'Invalid PDF: {error}') from error


def page_numbers(spec, count):
    result = []
    for part in spec.split(','):
        bounds = part.split('-')
        if len(bounds) not in {1, 2}:
            raise ValueError('Use page numbers or ranges such as 1,3-5')
        start, end = int(bounds[0]), int(bounds[-1])
        if not 1 <= start <= end <= count:
            raise ValueError('Page range is outside the document')
        result.extend(range(start - 1, end))
    return result


def process(inputs, output, pages=None, rotation=0):
    if not inputs or rotation not in {0, 90, 180, 270}:
        raise ValueError('Inputs and a rotation of 0, 90, 180, or 270 are required')
    if pages is not None and len(inputs) != 1:
        raise ValueError('Page selection requires exactly one input')
    output = Path(output)
    if output.exists() or any(output.resolve() == Path(item).resolve() for item in inputs):
        raise ValueError('Output must be a new file, different from every input')
    writer = PdfWriter()
    try:
        for source in inputs:
            document = reader(source)
            selected = page_numbers(pages, len(document.pages)) if pages is not None else range(len(document.pages))
            for index in selected:
                page = writer.add_page(document.pages[index])
                if rotation:
                    page.rotate(rotation)
        # Finish serialization before creating a destination. Exclusive create prevents clobbering.
        buffer = io.BytesIO()
        writer.write(buffer)
        with output.open('xb') as destination:
            destination.write(buffer.getvalue())
        return {'output': str(output), 'pages': len(writer.pages)}
    except PyPdfError as error:
        raise ValueError(f'PDF processing failed: {error}') from error
    finally:
        writer.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    info = commands.add_parser('info'); info.add_argument('input')
    merge = commands.add_parser('merge'); merge.add_argument('output'); merge.add_argument('inputs', nargs='+')
    extract = commands.add_parser('extract'); extract.add_argument('input'); extract.add_argument('output')
    extract.add_argument('--pages', required=True)
    rotate = commands.add_parser('rotate'); rotate.add_argument('input'); rotate.add_argument('output')
    rotate.add_argument('--degrees', type=int, choices=[90, 180, 270], required=True)
    args = parser.parse_args()
    def execute():
        if args.command == 'info':
            document = reader(args.input)
            return {'pages': len(document.pages), 'rotations': [page.rotation for page in document.pages]}
        if args.command == 'merge':
            return process(args.inputs, args.output)
        return process([args.input], args.output, getattr(args, 'pages', None), getattr(args, 'degrees', 0))
    run(execute)


if __name__ == '__main__':
    main()
