#!/usr/bin/env python3
"""
Claude Unwrapped
=================
Your year with Claude, in numbers.

Extracts and reports on all Claude-related data on your system.

Covers:
  - Claude Code CLI: sessions, history, settings, telemetry, plugins
  - Claude.ai data exports: conversations, thinking blocks, projects, memories

Usage:
  # Basic - scan Claude Code data only
  python3 claude_unwrapped.py

  # Include Claude.ai data exports (zip files from claude.ai/settings)
  python3 claude_unwrapped.py export1.zip export2.zip

  # Custom output path
  python3 claude_unwrapped.py --output ~/my_report.txt

  # Also copy all logs to a folder
  python3 claude_unwrapped.py --collect-logs ~/Desktop/my_claude_logs

Requirements: Python 3.8+, no external dependencies.
"""

import json
import os
import sys
import glob
import shutil
import zipfile
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sizeof_fmt(num):
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num) < 1024:
            return f"{num:3.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def safe_json_load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def count_files(path, pattern="*"):
    return len(glob.glob(os.path.join(path, pattern)))


def dir_size(path):
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def find_files(base, pattern):
    results = []
    for dirpath, _, filenames in os.walk(base):
        for f in filenames:
            if glob.fnmatch.fnmatch(f, pattern):
                results.append(os.path.join(dirpath, f))
    return results


W = 100  # report width


def banner(title):
    return f"\n{'=' * W}\n  {title}\n{'=' * W}\n"


def section_line():
    return "-" * 75


# ---------------------------------------------------------------------------
# Claude Code analysis
# ---------------------------------------------------------------------------

def analyze_claude_code(claude_dir):
    lines = []
    lines.append(banner("CLAUDE CODE CLI DATA"))

    if not os.path.isdir(claude_dir):
        lines.append(f"  Claude Code directory not found at {claude_dir}")
        return "\n".join(lines), {}

    # --- Disk usage ---
    total_size = dir_size(claude_dir)
    lines.append(f"  Directory: {claude_dir}")
    lines.append(f"  Total size: {sizeof_fmt(total_size)}")
    lines.append("")

    subdirs = [
        "projects", "shell-snapshots", "plugins", "file-history", "todos",
        "tasks", "telemetry", "paste-cache", "cache", "plans", "statsig",
        "backups", "sessions", "session-env", "chrome", "debug", "ide",
        "downloads",
    ]
    lines.append(f"  {'Subdirectory':<30} | {'Size':>10} | Files")
    lines.append(f"  {section_line()}")
    for sd in subdirs:
        p = os.path.join(claude_dir, sd)
        if os.path.isdir(p):
            sz = dir_size(p)
            fc = sum(1 for _, _, files in os.walk(p) for _ in files)
            lines.append(f"  {sd:<30} | {sizeof_fmt(sz):>10} | {fc}")

    # --- Config files ---
    lines.append(banner("CONFIGURATION"))
    config_files = [
        "settings.json", "settings.local.json", "remote-settings.json",
        "policy-limits.json", "mcp-needs-auth-cache.json",
    ]
    for cf in config_files:
        p = os.path.join(claude_dir, cf)
        if os.path.isfile(p):
            data = safe_json_load(p)
            lines.append(f"  {cf}:")
            if data:
                lines.append(f"    {json.dumps(data, indent=4)[:500]}")
            lines.append("")

    # --- Stats cache ---
    stats = {}
    stats_path = os.path.join(claude_dir, "stats-cache.json")
    if os.path.isfile(stats_path):
        stats = safe_json_load(stats_path) or {}

    if stats:
        lines.append(banner("USAGE STATISTICS"))
        lines.append(f"  Total sessions:    {stats.get('totalSessions', 'N/A')}")
        lines.append(f"  Total messages:    {stats.get('totalMessages', 'N/A')}")
        lines.append(f"  First session:     {stats.get('firstSessionDate', 'N/A')}")
        lines.append(f"  Stats cached to:   {stats.get('lastComputedDate', 'N/A')}")

        longest = stats.get("longestSession", {})
        if longest:
            dur_h = longest.get("duration", 0) / 3600000
            lines.append(f"  Longest session:   {dur_h:.1f} hours ({longest.get('messageCount', '?')} msgs)")

        # Model usage
        model_usage = stats.get("modelUsage", {})
        if model_usage:
            lines.append(f"\n  {'Model':<35} | {'Input':>12} | {'Output':>12} | {'Cache Read':>15}")
            lines.append(f"  {section_line()}")
            for model, u in model_usage.items():
                lines.append(
                    f"  {model:<35} | {u.get('inputTokens', 0):>12,} | "
                    f"{u.get('outputTokens', 0):>12,} | {u.get('cacheReadInputTokens', 0):>15,}"
                )

        # Daily activity
        daily = stats.get("dailyActivity", [])
        if daily:
            lines.append(f"\n  DAILY ACTIVITY ({len(daily)} days tracked):")
            lines.append(f"  {'Date':<12} | {'Messages':>8} | {'Sessions':>8} | {'Tool Calls':>10}")
            lines.append(f"  {section_line()}")
            for d in daily:
                lines.append(
                    f"  {d['date']:<12} | {d['messageCount']:>8,} | "
                    f"{d['sessionCount']:>8} | {d['toolCallCount']:>10,}"
                )

    # --- History ---
    history_path = os.path.join(claude_dir, "history.jsonl")
    if os.path.isfile(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            hist_lines = sum(1 for _ in f)
        lines.append(f"\n  Command history: {hist_lines:,} entries in history.jsonl")

    # --- Plugins ---
    plugins_path = os.path.join(claude_dir, "plugins", "installed_plugins.json")
    if os.path.isfile(plugins_path):
        pdata = safe_json_load(plugins_path)
        if pdata and "plugins" in pdata:
            lines.append(banner("INSTALLED PLUGINS"))
            lines.append(f"  {'Plugin':<45} | {'Version':<15} | {'Scope':<6} | Installed")
            lines.append(f"  {section_line()}")
            for name, entries in pdata["plugins"].items():
                for e in entries:
                    lines.append(
                        f"  {name:<45} | {e.get('version', '?'):<15} | "
                        f"{e.get('scope', '?'):<6} | {e.get('installedAt', '?')[:10]}"
                    )

    # --- Session JSONL analysis ---
    projects_dir = os.path.join(claude_dir, "projects")
    if os.path.isdir(projects_dir):
        lines.append(banner("SESSION LOG ANALYSIS"))
        main_jsonls = []
        sub_jsonls = []
        for f in find_files(projects_dir, "*.jsonl"):
            if "/subagents/" in f:
                sub_jsonls.append(f)
            else:
                main_jsonls.append(f)

        main_size = sum(os.path.getsize(f) for f in main_jsonls)
        sub_size = sum(os.path.getsize(f) for f in sub_jsonls)

        lines.append(f"  Main session files:    {len(main_jsonls)} ({sizeof_fmt(main_size)})")
        lines.append(f"  Subagent log files:    {len(sub_jsonls)} ({sizeof_fmt(sub_size)})")
        lines.append(f"  Combined:              {len(main_jsonls) + len(sub_jsonls)} ({sizeof_fmt(main_size + sub_size)})")

        # Parse a summary from all JSONL files
        entry_types = Counter()
        block_types = Counter()
        model_counts = Counter()
        thinking_count = 0
        thinking_chars = 0
        assistant_chars = 0
        user_chars = 0
        total_lines_parsed = 0
        timestamps = []

        all_jsonls = main_jsonls + sub_jsonls
        lines.append(f"\n  Parsing {len(all_jsonls)} JSONL files...")

        for fp in all_jsonls:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    for line in f:
                        total_lines_parsed += 1
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        etype = entry.get("type", "unknown")
                        entry_types[etype] += 1

                        ts = entry.get("timestamp")
                        if isinstance(ts, str) and ts:
                            timestamps.append(ts[:10])

                        msg = entry.get("message", {})
                        if not isinstance(msg, dict):
                            continue

                        model = msg.get("model")
                        if model:
                            model_counts[model] += 1

                        content = msg.get("content", [])
                        if not isinstance(content, list):
                            continue

                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            btype = block.get("type", "unknown")
                            role = msg.get("role", "unknown")
                            block_types[f"{role}:{btype}"] += 1

                            if btype == "thinking":
                                thinking_count += 1
                                t = block.get("thinking", "")
                                if t and len(t) > 50:
                                    thinking_chars += len(t)

                            elif btype == "text":
                                t = block.get("text", "")
                                if role == "assistant":
                                    assistant_chars += len(t)
                                elif role == "user":
                                    user_chars += len(t)

                            elif btype == "tool_result":
                                pass  # skip tool output

            except Exception:
                continue

        lines.append(f"  Total JSONL lines parsed: {total_lines_parsed:,}")
        lines.append("")

        if entry_types:
            lines.append(f"  {'Entry Type':<30} | Count")
            lines.append(f"  {section_line()}")
            for et, c in entry_types.most_common():
                lines.append(f"  {et:<30} | {c:,}")

        lines.append("")
        lines.append(f"  Assistant text chars:   {assistant_chars:>12,}  ({sizeof_fmt(assistant_chars)})")
        lines.append(f"  User text chars:        {user_chars:>12,}  ({sizeof_fmt(user_chars)})")
        lines.append(f"  Thinking blocks:        {thinking_count:>12,}")
        lines.append(f"  Thinking chars (readable): {thinking_chars:>9,}  ({sizeof_fmt(thinking_chars)})")

        if model_counts:
            lines.append(f"\n  {'Model':<40} | Messages")
            lines.append(f"  {section_line()}")
            for m, c in model_counts.most_common():
                lines.append(f"  {m:<40} | {c:,}")

        if timestamps:
            lines.append(f"\n  Date range: {min(timestamps)} to {max(timestamps)}")

    # --- Projects list ---
    if os.path.isdir(projects_dir):
        proj_dirs = [
            d for d in os.listdir(projects_dir)
            if os.path.isdir(os.path.join(projects_dir, d))
        ]
        lines.append(banner("PROJECTS TRACKED"))
        lines.append(f"  {len(proj_dirs)} projects:\n")
        for pd in sorted(proj_dirs):
            sz = dir_size(os.path.join(projects_dir, pd))
            lines.append(f"    {pd:<60} {sizeof_fmt(sz):>10}")

    # --- Versions ---
    versions_dir = os.path.expanduser("~/.local/share/claude/versions")
    if os.path.isdir(versions_dir):
        lines.append(banner("INSTALLED VERSIONS"))
        for v in sorted(os.listdir(versions_dir)):
            vp = os.path.join(versions_dir, v)
            if os.path.isfile(vp):
                lines.append(f"  {v:<15} {sizeof_fmt(os.path.getsize(vp)):>12}")

        symlink = os.path.expanduser("~/.local/bin/claude")
        if os.path.islink(symlink):
            lines.append(f"\n  Active: {os.readlink(symlink)}")

    # --- CLAUDE.md files ---
    home = os.path.expanduser("~")
    claude_mds = find_files(home, "CLAUDE.md")
    if claude_mds:
        lines.append(banner("CLAUDE.MD FILES FOUND"))
        for cm in claude_mds[:20]:
            try:
                sz = os.path.getsize(cm)
                lines.append(f"  {cm}  ({sizeof_fmt(sz)})")
            except OSError:
                lines.append(f"  {cm}")

    return "\n".join(lines), stats


# ---------------------------------------------------------------------------
# Claude.ai export analysis
# ---------------------------------------------------------------------------

def analyze_export(zip_path, label=""):
    lines = []
    lines.append(banner(f"CLAUDE.AI DATA EXPORT: {label}"))

    if not os.path.isfile(zip_path):
        lines.append(f"  File not found: {zip_path}")
        return "\n".join(lines)

    lines.append(f"  Source: {zip_path}")
    lines.append(f"  Size:   {sizeof_fmt(os.path.getsize(zip_path))}")

    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="claude_export_")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmpdir)
            lines.append(f"  Files:  {', '.join(zf.namelist())}")
    except Exception as e:
        lines.append(f"  Error extracting: {e}")
        return "\n".join(lines)

    # --- Users ---
    users = safe_json_load(os.path.join(tmpdir, "users.json")) or []
    lines.append(f"\n  Accounts: {len(users)}")
    for u in users:
        phone = u.get("verified_phone_number", "-") or "-"
        lines.append(f"    {u.get('full_name', '?'):<25} {u.get('email_address', '?'):<40} {phone}")

    # --- Projects ---
    projects = safe_json_load(os.path.join(tmpdir, "projects.json")) or []
    lines.append(f"\n  Projects: {len(projects)}")
    for p in projects[:30]:
        lines.append(f"    {p.get('name', '(unnamed)')}")

    # --- Memories ---
    memories = safe_json_load(os.path.join(tmpdir, "memories.json")) or []
    total_mem_chars = 0
    total_proj_mems = 0
    for m in memories:
        cm = m.get("conversations_memory", "")
        total_mem_chars += len(cm)
        pm = m.get("project_memories", {})
        total_proj_mems += len(pm)
        for v in pm.values():
            total_mem_chars += len(v)
    lines.append(f"\n  Memories: {len(memories)} entries, {total_proj_mems} project memories, {total_mem_chars:,} chars")

    # --- Conversations ---
    conv_path = os.path.join(tmpdir, "conversations.json")
    if not os.path.isfile(conv_path):
        lines.append("  No conversations.json found")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return "\n".join(lines)

    lines.append(f"\n  Parsing conversations (may take a moment for large files)...")

    try:
        with open(conv_path, "r", encoding="utf-8") as f:
            conversations = json.load(f)
    except Exception as e:
        lines.append(f"  Error parsing conversations: {e}")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return "\n".join(lines)

    total_convos = len(conversations)
    user_msgs = 0
    asst_msgs = 0
    user_chars = 0
    asst_chars = 0
    thinking_blocks = 0
    thinking_chars = 0
    tool_calls = Counter()
    monthly_counts = Counter()
    convos_with_thinking = 0
    dates = []
    msgs_per_convo = []
    per_user = defaultdict(lambda: {"convos": 0, "user_msgs": 0, "asst_msgs": 0, "user_chars": 0, "asst_chars": 0})
    longest_thinking = 0
    most_thinking_convo = ("", 0)

    for conv in conversations:
        created = conv.get("created_at", "")[:10]
        if created:
            dates.append(created)
            monthly_counts[created[:7]] += 1

        msgs = conv.get("chat_messages", [])
        msgs_per_convo.append(len(msgs))
        convo_thinking = 0
        convo_name = conv.get("name", "(unnamed)")
        account_uuid = conv.get("account_uuid") or conv.get("account", {}).get("uuid", "")

        # find user name from account uuid
        user_name = "unknown"
        for u in users:
            if u.get("uuid") == account_uuid:
                user_name = u.get("full_name", "unknown")
                break

        per_user[user_name]["convos"] += 1

        for msg in msgs:
            sender = msg.get("sender", "")
            content = msg.get("content", [])
            if not isinstance(content, list):
                content = [{"type": "text", "text": str(content)}]

            if sender == "human":
                user_msgs += 1
                per_user[user_name]["user_msgs"] += 1
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        chars = len(block.get("text", ""))
                        user_chars += chars
                        per_user[user_name]["user_chars"] += chars

            elif sender == "assistant":
                asst_msgs += 1
                per_user[user_name]["asst_msgs"] += 1
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type", "")

                    if btype == "text":
                        chars = len(block.get("text", ""))
                        asst_chars += chars
                        per_user[user_name]["asst_chars"] += chars

                    elif btype == "thinking":
                        thinking_blocks += 1
                        convo_thinking += 1
                        t = block.get("thinking", "")
                        tc = len(t)
                        thinking_chars += tc
                        if tc > longest_thinking:
                            longest_thinking = tc

                    elif btype == "tool_use":
                        tool_calls[block.get("name", "unknown")] += 1

        if convo_thinking > 0:
            convos_with_thinking += 1
        if convo_thinking > most_thinking_convo[1]:
            most_thinking_convo = (convo_name, convo_thinking)

    # --- Output stats ---
    lines.append(f"\n  {section_line()}")
    lines.append(f"  CONVERSATION STATISTICS")
    lines.append(f"  {section_line()}")
    lines.append(f"  Total conversations:     {total_convos:,}")
    if dates:
        lines.append(f"  Date range:              {min(dates)} to {max(dates)}")
    lines.append(f"  User messages:           {user_msgs:,}")
    lines.append(f"  Assistant messages:       {asst_msgs:,}")
    lines.append(f"  User chars:              {user_chars:,} ({sizeof_fmt(user_chars)})")
    lines.append(f"  Assistant chars:          {asst_chars:,} ({sizeof_fmt(asst_chars)})")

    if msgs_per_convo:
        lines.append(f"  Avg msgs/conversation:   {sum(msgs_per_convo) / len(msgs_per_convo):.1f}")
        lines.append(f"  Max msgs in one convo:   {max(msgs_per_convo)}")

    lines.append(f"\n  {section_line()}")
    lines.append(f"  THINKING BLOCKS")
    lines.append(f"  {section_line()}")
    lines.append(f"  Total thinking blocks:   {thinking_blocks:,}")
    lines.append(f"  Total thinking chars:    {thinking_chars:,} ({sizeof_fmt(thinking_chars)})")
    if thinking_blocks:
        lines.append(f"  Avg thinking length:     {thinking_chars // thinking_blocks:,} chars")
    lines.append(f"  Longest thinking block:  {longest_thinking:,} chars")
    lines.append(f"  Convos with thinking:    {convos_with_thinking} / {total_convos} ({100 * convos_with_thinking / max(total_convos, 1):.1f}%)")
    lines.append(f"  Most thinking-heavy:     {most_thinking_convo[0][:60]} ({most_thinking_convo[1]} blocks)")

    if tool_calls:
        lines.append(f"\n  {section_line()}")
        lines.append(f"  TOOL USAGE ({sum(tool_calls.values()):,} total calls)")
        lines.append(f"  {section_line()}")
        lines.append(f"  {'Tool':<40} | Calls")
        for tool, count in tool_calls.most_common(20):
            lines.append(f"  {tool:<40} | {count:,}")

    if monthly_counts:
        lines.append(f"\n  {section_line()}")
        lines.append(f"  MONTHLY CONVERSATION COUNTS")
        lines.append(f"  {section_line()}")
        for month in sorted(monthly_counts):
            lines.append(f"  {month}:  {monthly_counts[month]}")

    if len(per_user) > 1:
        lines.append(f"\n  {section_line()}")
        lines.append(f"  PER-USER BREAKDOWN")
        lines.append(f"  {section_line()}")
        lines.append(f"  {'User':<25} | {'Convos':>6} | {'User Msgs':>9} | {'Asst Msgs':>9} | {'User Chars':>10} | {'Asst Chars':>10}")
        for uname, ud in sorted(per_user.items(), key=lambda x: -x[1]["convos"]):
            lines.append(
                f"  {uname:<25} | {ud['convos']:>6} | {ud['user_msgs']:>9} | "
                f"{ud['asst_msgs']:>9} | {ud['user_chars']:>10,} | {ud['asst_chars']:>10,}"
            )

    shutil.rmtree(tmpdir, ignore_errors=True)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Log collection
# ---------------------------------------------------------------------------

def collect_logs(claude_dir, export_zips, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    summary = [f"Collecting logs to: {dest_dir}\n"]

    # Claude Code history
    hist_dir = os.path.join(dest_dir, "claude_code_history")
    os.makedirs(hist_dir, exist_ok=True)
    src = os.path.join(claude_dir, "history.jsonl")
    if os.path.isfile(src):
        shutil.copy2(src, hist_dir)
        summary.append(f"  Copied history.jsonl")

    # Claude Code sessions
    sess_dir = os.path.join(dest_dir, "claude_code_sessions")
    os.makedirs(sess_dir, exist_ok=True)
    projects_dir = os.path.join(claude_dir, "projects")
    if os.path.isdir(projects_dir):
        for f in find_files(projects_dir, "*.jsonl"):
            if "/subagents/" not in f:
                shutil.copy2(f, sess_dir)
        summary.append(f"  Copied {count_files(sess_dir, '*.jsonl')} session files")

    # Claude Code subagents
    sub_dir = os.path.join(dest_dir, "claude_code_subagents")
    os.makedirs(sub_dir, exist_ok=True)
    if os.path.isdir(projects_dir):
        for f in find_files(projects_dir, "*.jsonl"):
            if "/subagents/" in f:
                shutil.copy2(f, sub_dir)
        summary.append(f"  Copied {count_files(sub_dir, '*.jsonl')} subagent files")

    # Config
    cfg_dir = os.path.join(dest_dir, "claude_code_config")
    os.makedirs(cfg_dir, exist_ok=True)
    for cf in ["stats-cache.json", "settings.json", "settings.local.json"]:
        src = os.path.join(claude_dir, cf)
        if os.path.isfile(src):
            shutil.copy2(src, cfg_dir)

    # Telemetry
    tel_dir = os.path.join(dest_dir, "claude_code_telemetry")
    os.makedirs(tel_dir, exist_ok=True)
    tel_src = os.path.join(claude_dir, "telemetry")
    if os.path.isdir(tel_src):
        for f in glob.glob(os.path.join(tel_src, "*.json")):
            shutil.copy2(f, tel_dir)

    # Plans
    plan_dir = os.path.join(dest_dir, "claude_code_plans")
    os.makedirs(plan_dir, exist_ok=True)
    plan_src = os.path.join(claude_dir, "plans")
    if os.path.isdir(plan_src):
        for f in glob.glob(os.path.join(plan_src, "*.md")):
            shutil.copy2(f, plan_dir)

    # Extract exports
    for i, zp in enumerate(export_zips, 1):
        if os.path.isfile(zp):
            exp_dir = os.path.join(dest_dir, f"claude_ai_export_{i}")
            os.makedirs(exp_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(zp, "r") as zf:
                    zf.extractall(exp_dir)
                summary.append(f"  Extracted export {i} to {exp_dir}")
            except Exception as e:
                summary.append(f"  Error extracting {zp}: {e}")

    total = dir_size(dest_dir)
    summary.append(f"\n  Total collected: {sizeof_fmt(total)}")
    return "\n".join(summary)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Claude Unwrapped - your year with Claude, in numbers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 claude_intelligence_extractor.py
  python3 claude_intelligence_extractor.py ~/Downloads/export1.zip ~/Downloads/export2.zip
  python3 claude_intelligence_extractor.py --output ~/report.txt --collect-logs ~/Desktop/logs
        """,
    )
    parser.add_argument(
        "exports", nargs="*",
        help="Claude.ai data export zip files (download from claude.ai/settings)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output report path (default: ~/Desktop/claude_unwrapped_report.txt)",
    )
    parser.add_argument(
        "--collect-logs", default=None,
        help="Copy all logs to this folder",
    )
    parser.add_argument(
        "--claude-dir", default=None,
        help="Claude Code directory (default: ~/.claude)",
    )
    args = parser.parse_args()

    claude_dir = args.claude_dir or os.path.expanduser("~/.claude")
    output_path = args.output or os.path.expanduser("~/Desktop/claude_unwrapped_report.txt")

    report = []
    report.append("=" * W)
    report.append("               CLAUDE UNWRAPPED")
    report.append("=" * W)
    report.append(f"  Generated:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"  System:     {os.uname().sysname} {os.uname().release}")
    report.append(f"  User:       {os.environ.get('USER', 'unknown')}")
    report.append(f"  Home:       {os.path.expanduser('~')}")
    report.append(f"  Claude dir: {claude_dir}")
    report.append("=" * W)

    # Analyze Claude Code
    print("Scanning Claude Code data...")
    code_report, stats = analyze_claude_code(claude_dir)
    report.append(code_report)

    # Analyze exports
    for i, zp in enumerate(args.exports, 1):
        print(f"Analyzing export {i}: {zp}...")
        export_report = analyze_export(zp, label=f"Export #{i} ({os.path.basename(zp)})")
        report.append(export_report)

    # Collect logs
    if args.collect_logs:
        print(f"Collecting logs to {args.collect_logs}...")
        log_summary = collect_logs(claude_dir, args.exports, args.collect_logs)
        report.append(banner("LOG COLLECTION"))
        report.append(log_summary)

    # Footer
    report.append("\n" + "=" * W)
    report.append("  END OF REPORT")
    report.append("=" * W)

    # Write report
    full_report = "\n".join(report)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_report)

    print(f"\nReport saved to: {output_path}")
    print(f"Report size: {sizeof_fmt(len(full_report.encode('utf-8')))}")

    if args.collect_logs:
        print(f"Logs collected to: {args.collect_logs}")


if __name__ == "__main__":
    main()
