"""JSON command line and line-oriented agent interface."""

import argparse
import json
import sys

from .runtime import Lab


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
        except (ValueError, TypeError) as exc:
            request_id = request.get("id") if isinstance(request, dict) else None
            reply = {"id": request_id, "error": {"type": type(exc).__name__, "message": str(exc)}}
        print(json.dumps(reply, ensure_ascii=False, allow_nan=False), flush=True)


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
    act = commands.add_parser("act")
    act.add_argument("session")
    act.add_argument("action")
    act.add_argument("params", nargs="?", default="{}")
    act.add_argument("--operation-id")
    act.add_argument("--revision", type=int)
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
            elif args.command == "act":
                result = lab.act(
                    args.session,
                    args.action,
                    json.loads(args.params),
                    operation_id=args.operation_id,
                    expected_revision=args.revision,
                )
            elif args.command == "fork":
                result = lab.fork(
                    args.session, at_revision=args.revision, session_id_new=args.id
                ).status()
            elif args.command == "history":
                result = lab.history(args.session, after=args.after)
            elif args.command == "export":
                result = {"records": lab.export(args.session, args.path), "path": args.path}
            elif args.command == "serve":
                protocol(lab)
                return
            elif args.command == "mcp":
                from .integrations.mcp import server

                server(lab).run(transport="stdio")
                return
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, TypeError, ImportError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
