#!/usr/bin/env python3
"""
Mock solver script for testing solver execution
Simulates message_ix solver behavior
"""

import sys
import time
import random

def main():
    if len(sys.argv) < 3:
        print("Usage: mock_solver.py <input_file> <solver_name>")
        sys.exit(1)

    input_file = sys.argv[1]
    solver_name = sys.argv[2]

    print(f"Mock message_ix Solver starting...")
    print(f"Input file: {input_file}")
    print(f"Solver: {solver_name}")
    print(f"Python version: {sys.version}")
    print()

    # Simulate solver initialization
    print("Initializing model...")
    time.sleep(1)

    print("Loading parameters...")
    time.sleep(0.5)

    print("Setting up optimization problem...")
    time.sleep(0.5)

    # Simulate solver iterations
    max_iterations = random.randint(5, 15)
    for i in range(1, max_iterations + 1):
        print(f"Iteration {i}/{max_iterations}: Objective = {random.uniform(1000, 5000):.2f}")
        time.sleep(random.uniform(0.2, 0.8))

        # Occasionally show solver-specific messages
        if random.random() < 0.3:
            messages = [
                "Presolving model...",
                "Solving LP relaxation...",
                "Applying cuts...",
                "Branching on variable...",
                "Checking feasibility..."
            ]
            print(random.choice(messages))

    # Simulate final result
    success = random.random() > 0.2  # 80% success rate

    if success:
        print()
        print("OPTIMAL SOLUTION FOUND")
        print(f"Final objective value: {random.uniform(2000, 4000):.2f}")
        print("Solution time: 2.34 seconds")
        print("Status: Optimal")
        print()
        print("Solver completed successfully!")
        sys.exit(0)
    else:
        print()
        print("SOLVER FAILED")
        print("Error: Infeasible problem or numerical difficulties")
        print()
        print("Solver failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
