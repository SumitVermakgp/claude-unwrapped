# claude-unwrapped

Your year with Claude, in numbers.

One script. No dependencies. Generates a visual report from your Claude data.

## Quick start

```bash
git clone https://github.com/Responsible-AI-Labs/claude-unwrapped.git
cd claude-unwrapped
python3 claude_unwrapped.py
```

The script will scan your Claude Code data, ask for Claude.ai exports, and generate a report.

## What you get

A branded HTML report covering:

- Usage stats, conversation lengths, output-to-input ratio
- Monthly activity chart
- Claude's verbosity trend (did it get more concise with you?)
- Apology rate over time
- Frustration detection, recovery rate, median messages to recover
- Sycophancy check (pressure-triggered vs factual agreement)
- Friction trend with actual chat excerpts from heated moments
- "Start over" pattern detection
- Dynamic insights generated from YOUR data (marathon conversations, abandoned ratio, voice input detection, cursing dynamics, streaks, night owl / early bird, typing pattern shifts, Claude's role evolution)
- Topic evolution by quarter
- Tool usage breakdown
- Claude Code CLI stats

## How to get your data

**Claude.ai**: Go to [claude.ai/settings](https://claude.ai/settings), click Export Data. You get a .zip.

**Claude Code**: Already at `~/.claude/` on your machine. The script reads it automatically.

## Usage

```bash
# Interactive (recommended)
python3 claude_unwrapped.py

# With exports directly
python3 claude_unwrapped.py ~/Downloads/export.zip

# Multiple exports (personal + work accounts)
python3 claude_unwrapped.py personal.zip work.zip

# Options
python3 claude_unwrapped.py --output ~/report.html --claude-dir ~/.claude --no-interactive
```

Output is a self-contained HTML file. Open in browser, Cmd+P to save as PDF.

## Requirements

Python 3.8+. Zero pip installs.

## Privacy

Runs locally. Nothing sent anywhere.

## License

MIT

## Author

[Responsible AI Labs](https://responsibleailabs.ai)
