# Legislative Skills for Claude Code

AI agent skills for legislative research, bill tracking, policy analysis, and civic engagement.

Built for policy analysts, lobbyists, advocates, journalists, and civic-engaged citizens.

## Installation

### Quick Install (Recommended)

```bash
npx skills add bryceweiner/legislativeskills
```

### Manual Install

Clone the repository and copy the skills folder to your Claude Code project:

```bash
git clone https://github.com/bryceweiner/legislativeskills.git
cp -r legislativeskills/skills .claude/skills/
```

### Requirements

This toolkit requires a [LegiScan API key](https://legiscan.com/legiscan). Set it as an environment variable:

```bash
export LEGISCAN_API_KEY=your_api_key_here
```

For the dashboard and report tools, install Python dependencies:

```bash
pip install requests flask reportlab pdfplumber
```

## Available Skills

### Research & Discovery

| Skill | Description |
|-------|-------------|
| `/search-bills` | Search for legislation by keyword across any U.S. state |
| `/read-bill` | Fetch and display the actual statutory text of a bill |
| `/explain-bill` | Plain-English explanation of what a bill does and who it affects |
| `/track-topic` | Show all legislation on a policy topic in a state or nationally |
| `/compare-states` | Side-by-side analysis of how multiple states approach a topic |

### Legislator & Voting

| Skill | Description |
|-------|-------------|
| `/my-rep-votes` | Find how a specific legislator voted on a bill with party breakdown |

### Personal Tracking

| Skill | Description |
|-------|-------------|
| `/docket` | Manage your personal bill tracking list with stance, priority, and notes |
| `/docket-report` | Generate a status report for all bills you're tracking |
| `/monitor-bill` | Add/remove bills from your LegiScan monitor list |
| `/check-updates` | Check for changes to monitored bills using change detection |

### Reporting

| Skill | Description |
|-------|-------------|
| `/generate-report` | Generate a formatted PDF policy impact report |

## Usage Examples

### Search for Bills

```
/search-bills cannabis legalization CO
/search-bills "sports betting" TX 2024
```

### Explain a Bill

```
/explain-bill TX HB1234
/explain-bill 1423040
```

### Track Your Issues

```
/docket add TX HB1234 support high "Key priority bill"
/docket list
/docket-report
```

### Compare State Approaches

```
/compare-states cannabis legalization CO,CA,OR
/compare-states minimum wage NY,CA,WA
```

### Generate Reports

```
/generate-report TX HB1234
```

## Tools Included

The `tools/` directory contains Python utilities that power the skills:

| Tool | Description |
|------|-------------|
| `legiscan_client.py` | Core API client with caching, monitoring, and docket management |
| `generate_dashboard.py` | Flask web dashboard for bill analysis |
| `generate_report.py` | PDF report generator |

### Run the Dashboard

```bash
cd tools
python generate_dashboard.py 1423040
# Opens at http://localhost:5000
```

## Data Source

All legislative data is sourced from [LegiScan](https://legiscan.com/), which provides:
- Coverage of all 50 U.S. states + Congress
- Real-time bill tracking and change detection
- Full bill text, vote records, and sponsor information
- Historical legislative data

## Project Structure

```
legislativeskills/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── AGENTS.md
├── skills/                    # Claude Code skill definitions
│   ├── search-bills.md
│   ├── explain-bill.md
│   ├── read-bill.md
│   ├── track-topic.md
│   ├── compare-states.md
│   ├── my-rep-votes.md
│   ├── generate-report.md
│   ├── docket.md
│   ├── docket-report.md
│   ├── monitor-bill.md
│   └── check-updates.md
├── tools/                     # Python infrastructure
│   ├── legiscan_client.py
│   ├── generate_dashboard.py
│   └── generate_report.py
└── .claude/
    └── settings.json
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding new skills or improving existing ones.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Built by [Bryce Johnston](https://github.com/brycej98)

---

**Note:** This project is not affiliated with LegiScan. You must obtain your own API key and comply with LegiScan's terms of service.
