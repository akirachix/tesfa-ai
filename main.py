import logging, os, sys, importlib
logger = logging.getLogger("adk_startup")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[adk_startup] %(levelname)s %(message)s"))
logger.addHandler(handler)
cwd = os.path.dirname(os.path.abspath(__file__))
candidates = [
    os.path.join(cwd, "tesfa_agent"),
    "/app/agents/tesfa_agent",
    "/app/tesfa_agent",
    os.environ.get("AGENTS_DIR"),
    os.environ.get("ADK_AGENTS_DIR"),
]
logger.info("Startup debug — scanning possible agent dirs")
for p in candidates:
    if not p:
        logger.info(f"candidate: {p} (skipped)")
        continue
    try:
        exists = os.path.exists(p)
        listing = os.listdir(p) if exists else None
        logger.info(f"candidate: {p} exists={exists} listing={listing}")
    except Exception as e:
        logger.info(f"candidate: {p} error={e}")

AGENT_DIR = next((p for p in candidates if p and os.path.exists(p)), candidates[0])
logger.info(f"Using AGENT_DIR -> {AGENT_DIR}")

try:

    parent = os.path.dirname(AGENT_DIR) if AGENT_DIR else cwd
    if parent and parent not in sys.path:
        sys.path.insert(0, parent)
    pkg = importlib.import_module("tesfa_agent")
    logger.info(f"import tesfa_agent OK, attrs: {', '.join([a for a in dir(pkg) if 'root' in a or a=='root_agent'])}")
    logger.info(f"hasattr(root_agent)={hasattr(pkg, 'root_agent')}")
except Exception as e:
    logger.exception("Import tesfa_agent failed")





