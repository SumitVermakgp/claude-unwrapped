# claude-unwrapped

Your year with Claude, in numbers. Like Spotify Wrapped, but for your AI conversations.

**Extract, analyze, and visualize every interaction you've had with Claude** across Claude.ai (personal + team accounts) and Claude Code CLI.

```
$ python3 claude_unwrapped.py

Scanning Claude Code data...
Analyzing export 1: personal_export.zip...
Analyzing export 2: work_export.zip...

Report saved to: ~/Desktop/claude_unwrapped_report.txt
```

## What it finds

**Claude Code CLI** (`~/.claude/`)
- Total sessions, messages, tool calls, token usage by model
- Daily activity log with message counts and tool call breakdowns
- Session duration analysis (including your longest marathon session)
- Installed plugins, permission rules, MCP integrations
- Project-by-project disk usage and activity
- CLAUDE.md files found across your system
- Installed binary versions and disk footprint

**Claude.ai Data Exports** (personal and team accounts)
- Conversation counts, message volumes, character counts
- Per-user breakdown (who on your team uses Claude the most)
- Thinking block analysis (count, length, frequency)
- Tool usage rankings (bash, web_search, create_file, etc.)
- Monthly conversation trends
- Project and memory summaries

**Combined**
- Cross-platform aggregate totals
- Full timeline from first conversation to today

## Setup

Python 3.8+. No external dependencies. Zero pip installs.

```bash
git clone https://github.com/SumitVermakgp/claude-unwrapped.git
cd claude-unwrapped
```

## Usage

### Basic: scan Claude Code data only

```bash
python3 claude_unwrapped.py
```

### Include Claude.ai data exports

Download your data from [claude.ai/settings](https://claude.ai/settings) (look for "Export Data"). Then:

```bash
python3 claude_unwrapped.py ~/Downloads/export_personal.zip ~/Downloads/export_work.zip
```

### Custom output path

```bash
python3 claude_unwrapped.py --output ~/my_report.txt
```

### Collect all raw logs into a folder

This copies session logs, subagent files, configs, telemetry, plans, and extracted exports into one folder for further analysis:

```bash
python3 claude_unwrapped.py --collect-logs ~/Desktop/my_claude_logs export1.zip export2.zip
```

### Specify a custom Claude directory

```bash
python3 claude_unwrapped.py --claude-dir /path/to/.claude
```

## How to get your data

| Source | How |
|---|---|
| **Claude.ai conversations** | Go to [claude.ai/settings](https://claude.ai/settings), click "Export Data". You'll get a zip with `conversations.json`, `projects.json`, `memories.json`, and `users.json`. |
| **Claude Code local data** | Already on your machine at `~/.claude/`. The script reads it automatically. |

If you have both a personal and a work/team Claude.ai account, export both and pass them as arguments.

## Sample output

```
====================================================================================================
               CLAUDE INTELLIGENCE REPORT
====================================================================================================
  Generated:  2026-04-16 21:30:00
  System:     Darwin 25.3.0
  User:       yourname
  Claude dir: /Users/yourname/.claude
====================================================================================================

  Total sessions:    100
  Total messages:    47,717
  First session:     2025-12-29 09:42:56 UTC
  Longest session:   36.5 hours (32 msgs)

  Model                              |  Input Tokens |  Output Tokens |  Cache Read
  ---------------------------------------------------------------------------
  claude-opus-4-5-20251101           |    1,172,154  |    1,664,710   |  1,195,892,371
  claude-opus-4-6                    |       46,853  |      137,411   |    151,776,012
```

## What you can do with the output

- Feed the report back into Claude and ask it to find behavioral patterns
- Track how your usage evolves month over month
- Find your most productive days and longest sessions
- See which tools and models you rely on
- Compare usage across team members
- Identify your frustration patterns and recovery dynamics
- Share your stats (like [this post](https://www.linkedin.com/in/sumitvermakgp/))

## Privacy

Everything runs locally. No data is sent anywhere. The script reads files that are already on your machine and produces a local text report. The Claude.ai exports are zip files you download yourself.

## License

MIT

## Author

[Sumit Verma](https://github.com/SumitVermakgp) -- Co-Founder & CTO, [Responsible AI Labs](https://responsibleailabs.ai)

Built after discovering that Claude Code started saying things like "Sorry, I was overthinking" and "Agreed, I can't beat you on this" -- which made me curious enough to audit a full year of conversations.
