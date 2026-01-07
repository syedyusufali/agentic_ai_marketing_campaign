#!/usr/bin/env python3
"""
Agentic AI Marketing Campaign Planner

An AI-native marketing platform with autonomous agents for:
- Customer segmentation
- Content generation
- Workflow automation
- Analytics and predictions

Usage:
    python main.py                  # Interactive mode
    python main.py --demo           # Load demo data and start
    python main.py "your query"     # Single query mode
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from cdp.storage import CDPStorage
from cdp.ingestion import DataIngestion
from agents.orchestrator import OrchestratorAgent


class MarketingPlatform:
    """
    Main platform class that initializes all components.
    """

    def __init__(self, db_path: str = "data/marketing_platform.db"):
        print("Initializing Agentic AI Marketing Platform...")

        # Initialize storage
        self.storage = CDPStorage(db_path)

        # Initialize orchestrator (which initializes all agents)
        self.orchestrator = OrchestratorAgent(self.storage)

        # Initialize data ingestion
        self.ingestion = DataIngestion(self.storage)

        print("Platform ready!\n")

    def load_demo_data(self, num_customers: int = 100):
        """Load demo customer and event data"""
        print(f"Generating {num_customers} sample customers with events...")
        stats = self.ingestion.generate_sample_data(num_customers)
        print(f"Created {stats['customers_imported']} customers")
        print(f"Generated {stats['events_imported']} events")
        if stats['errors']:
            print(f"Errors: {len(stats['errors'])}")
        print()

    def process(self, user_input: str) -> str:
        """Process user input through the orchestrator"""
        return self.orchestrator.process(user_input)

    def get_stats(self) -> dict:
        """Get platform statistics"""
        return self.storage.get_stats()


def print_banner():
    """Print welcome banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     AGENTIC AI MARKETING CAMPAIGN PLANNER                     ║
║                                                               ║
║     An AI-native platform for enterprise marketing            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_quick_start():
    """Print quick start guide"""
    guide = """
Quick Start Commands:
─────────────────────
  help                          Show all available commands
  status                        Show platform dashboard
  list segments                 List all segments
  list campaigns                List all campaigns

Example Requests:
─────────────────
  "Create a segment for high-value customers"
  "Write a welcome email for new users"
  "Build an onboarding workflow"
  "Show me churn predictions"
  "Create a winback campaign for inactive users"

Type 'exit' or 'quit' to exit.
"""
    print(guide)


def interactive_mode(platform: MarketingPlatform):
    """Run interactive CLI mode"""
    print_banner()
    print_quick_start()

    # Show current stats
    stats = platform.get_stats()
    print(f"Current data: {stats['total_customers']} customers, "
          f"{stats['total_segments']} segments, "
          f"{stats['total_campaigns']} campaigns\n")

    while True:
        try:
            # Get user input
            user_input = input("\n> ").strip()

            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            # Process input
            response = platform.process(user_input)
            print(f"\n{response}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


def single_query_mode(platform: MarketingPlatform, query: str):
    """Run single query and exit"""
    response = platform.process(query)
    print(response)


def main():
    parser = argparse.ArgumentParser(
        description="Agentic AI Marketing Campaign Planner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                              # Interactive mode
  python main.py --demo                       # Load demo data and start
  python main.py "Show me platform health"   # Single query
  python main.py --demo -n 500               # Load 500 demo customers
        """
    )

    parser.add_argument(
        'query',
        nargs='?',
        help='Single query to execute (optional)'
    )

    parser.add_argument(
        '--demo',
        action='store_true',
        help='Load demo/sample data on startup'
    )

    parser.add_argument(
        '-n', '--num-customers',
        type=int,
        default=100,
        help='Number of demo customers to generate (default: 100)'
    )

    parser.add_argument(
        '--db',
        type=str,
        default='data/marketing_platform.db',
        help='Database path (default: data/marketing_platform.db)'
    )

    args = parser.parse_args()

    # Initialize platform
    platform = MarketingPlatform(db_path=args.db)

    # Load demo data if requested
    if args.demo:
        platform.load_demo_data(args.num_customers)

    # Run in appropriate mode
    if args.query:
        single_query_mode(platform, args.query)
    else:
        interactive_mode(platform)


if __name__ == "__main__":
    main()
