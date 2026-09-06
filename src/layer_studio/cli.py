import argparse
import json
import sys

from .core import archive_attempt, build, init_job, verify


def main(argv=None):
    parser = argparse.ArgumentParser(description="Archive and assemble localized asset candidates locally.")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Preserve a PNG and prepare source analysis")
    init.add_argument("source")
    init.add_argument("job")
    init.add_argument("--asset", required=True)
    init.add_argument("--locale", default="ko")
    archive = commands.add_parser("archive", help="Preserve a generation output, prompt and references")
    archive.add_argument("job")
    archive.add_argument("record")
    assemble = commands.add_parser("build", help="Copy prepared layers, compose PNG and export a layered PSD")
    assemble.add_argument("job")
    assemble.add_argument("spec")
    check = commands.add_parser("verify", help="Reopen PSD and verify archived file hashes")
    check.add_argument("job")
    check.add_argument("revision")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init_job(args.source, args.job, args.asset, args.locale)
        elif args.command == "archive":
            result = archive_attempt(args.job, args.record)
        elif args.command == "build":
            result = build(args.job, args.spec)
        else:
            result = verify(args.job, args.revision)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
