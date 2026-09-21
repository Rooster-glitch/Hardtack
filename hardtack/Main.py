# Add this to the parser setup section:
    p_prune = sub.add_parser("prune", help="Archive old entries and start a new chain")
    p_prune.add_argument("--before", required=True, help="ISO Timestamp (e.g., 2026-01-01T00:00:00)")

# Add this to the command execution section (elif chain):
    elif args.command == "prune":
        count = ledger.prune(args.before)
        sys.exit(0 if count >= 0 else 1)
