"""JSON command line and line-oriented agent interface."""

import argparse
import json
import sys

from .runtime import Lab, OperationFailed
from .worker import Worker


def dispatch(lab, request):
    if not isinstance(request, dict):
        raise ValueError("A request must be a JSON object")
    method = request.get("method")
    params = request.get("params", {})
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    if method == "catalogue":
        if params:
            raise ValueError("catalogue takes no parameters")
        return lab.catalogue()
    if method == "sessions":
        if params:
            raise ValueError("sessions takes no parameters")
        return lab.list_sessions()
    if method == "create":
        return lab.create(**params).status()
    if method == "status":
        return lab.status(**params)
    if method == "act":
        return lab.act(**params)
    if method == "submit":
        return lab.submit(**params)
    if method == "operation":
        return lab.operation(**params)
    if method == "fork":
        return lab.fork(**params).status()
    if method == "history":
        return lab.history(**params)
    raise ValueError(f"Unknown method {method!r}")


def protocol(lab):
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            result = dispatch(lab, request)
            reply = {"id": request.get("id"), "result": result}
        except (ValueError, TypeError, OperationFailed) as exc:
            request_id = request.get("id") if isinstance(request, dict) else None
            reply = {"id": request_id, "error": {"type": type(exc).__name__, "message": str(exc)}}
        print(json.dumps(reply, ensure_ascii=False, allow_nan=False), flush=True)


def operation_parser(commands, name, help_text):
    parser = commands.add_parser(name, help=help_text)
    parser.add_argument("session")
    parser.add_argument("action")
    parser.add_argument("params", nargs="?", default="{}")
    parser.add_argument("--operation-id")
    parser.add_argument("--revision", type=int)
    return parser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="synthetic-lab.sqlite")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Describe models, controls and units")
    commands.add_parser("sessions", help="List persisted sessions")
    create = commands.add_parser("create")
    create.add_argument("model")
    create.add_argument("--seed", type=int)
    create.add_argument("--id")
    create.add_argument("--config", default="{}", help="Model configuration JSON")
    status = commands.add_parser("status")
    status.add_argument("session")
    operation_parser(commands, "act", "Execute an operation and wait for its result")
    operation_parser(commands, "submit", "Queue an operation and return immediately")
    operation = commands.add_parser("operation", help="Read a queued operation")
    operation.add_argument("session")
    operation.add_argument("operation_id")
    fork = commands.add_parser("fork")
    fork.add_argument("session")
    fork.add_argument("--revision", type=int)
    fork.add_argument("--id")
    history = commands.add_parser("history")
    history.add_argument("session")
    history.add_argument("--after", type=int, default=0)
    export = commands.add_parser("export")
    export.add_argument("session")
    export.add_argument("path")
    worker = commands.add_parser("worker", help="Execute queued operations")
    worker.add_argument("--model", action="append", dest="models")
    worker.add_argument("--id")
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--lease", type=float, default=300.0)
    worker.add_argument("--poll", type=float, default=0.1)
    commands.add_parser("serve", help="Read JSON requests, one per line on stdin")
    commands.add_parser("mcp", help="Run the optional MCP stdio server")
    args = parser.parse_args()
    try:
        with Lab(args.db) as lab:
            if args.command == "list":
                result = lab.catalogue()
            elif args.command == "sessions":
                result = lab.list_sessions()
            elif args.command == "create":
                result = lab.create(
                    args.model, seed=args.seed, session_id=args.id, config=json.loads(args.config)
                ).status()
            elif args.command == "status":
                result = lab.status(args.session)
            elif args.command in ("act", "submit"):
                method = lab.act if args.command == "act" else lab.submit
                result = method(
                    args.session,
                    args.action,
                    json.loads(args.params),
                    operation_id=args.operation_id,
                    expected_revision=args.revision,
                )
            elif args.command == "operation":
                result = lab.operation(args.session, args.operation_id)
            elif args.command == "fork":
                result = lab.fork(
                    args.session, at_revision=args.revision, session_id_new=args.id
                ).status()
            elif args.command == "history":
                result = lab.history(args.session, after=args.after)
            elif args.command == "export":
                result = {"records": lab.export(args.session, args.path), "path": args.path}
            elif args.command == "worker":
                process = Worker(
                    lab,
                    models=args.models,
                    worker_id=args.id,
                    lease_seconds=args.lease,
                    poll_seconds=args.poll,
                )
                if args.once:
                    result = process.run_once()
                else:
                    try:
                        process.serve()
                    except KeyboardInterrupt:
                        return
                    return
            elif args.command == "serve":
                protocol(lab)
                return
            elif args.command == "mcp":
                from .integrations.mcp import server

                server(lab).run(transport="stdio")
                return
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, TypeError, ImportError, OperationFailed) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
