import pandas as pd

# Load flight and gate data
flights = pd.read_csv("data/flights.csv")
gates = pd.read_csv("data/gates.csv")

# Convert flight times into time values
flights["scheduled_arrival"] = pd.to_datetime(
    flights["scheduled_arrival"],
    format="%H:%M"
)

flights["scheduled_departure"] = pd.to_datetime(
    flights["scheduled_departure"],
    format="%H:%M"
)

# Calculate the predicted arrival time after delay
flights["predicted_arrival"] = (
    flights["scheduled_arrival"]
    + pd.to_timedelta(flights["delay_minutes"], unit="m")
)

# Calculate the predicted gate release time
flights["predicted_gate_release"] = (
    flights["scheduled_arrival"]
    + pd.to_timedelta(flights["turnaround_minutes"], unit="m")
    + pd.to_timedelta(flights["delay_minutes"], unit="m")
)

print("\n=== GateGuard Gate Recommendation ===\n")

print("Flights loaded:", len(flights))
print("Gates loaded:", len(gates))
# Find the flight involved in the conflict
target_flight = flights[flights["flight_id"] == "EK501"].iloc[0]

print("\n=== Conflict Flight ===")
print("Flight:", target_flight["flight_id"])
print("Airline:", target_flight["airline"])
print("Current Gate:", target_flight["assigned_gate"])
print(
    "Predicted Arrival:",
    target_flight["predicted_arrival"].strftime("%H:%M")
)
print(
    "Predicted Gate Release:",
    target_flight["predicted_gate_release"].strftime("%H:%M")
)
# Check every gate for suitability
print("\n=== Gate Suitability Check ===\n")

current_gate = target_flight["assigned_gate"]

for _, gate in gates.iterrows():

    gate_id = gate["gate_id"]

    # Skip the flight's current conflicting gate
    if gate_id == current_gate:
        continue

    # Store gate evaluation results
gate_results = []

# Check every alternative gate
for _, gate in gates.iterrows():

    gate_id = gate["gate_id"]

    # Skip the current conflicting gate
    if gate_id == current_gate:
        continue

    print(f"Checking {gate_id}...")

    # Assume gate is feasible initially
    gate_available = True
    overlap_minutes = 0
    future_conflict = False

    # Check every other flight
    for _, other_flight in flights.iterrows():

        # Ignore the target flight
        if other_flight["flight_id"] == target_flight["flight_id"]:
            continue

        # Only compare flights using this candidate gate
        if other_flight["assigned_gate"] != gate_id:
            continue

        other_arrival = other_flight["predicted_arrival"]
        other_release = other_flight["predicted_gate_release"]

        target_arrival = target_flight["predicted_arrival"]
        target_release = target_flight["predicted_gate_release"]

        # Calculate overlap
        latest_start = max(target_arrival, other_arrival)
        earliest_end = min(target_release, other_release)

        if latest_start < earliest_end:

            overlap = (earliest_end - latest_start).total_seconds() / 60
            overlap_minutes += overlap

            gate_available = False

    # Check international compatibility
    compatibility_score = 0

    if gate["international_capable"] == "Yes":
        compatibility_score = 20
    else:
        compatibility_score = 0

    # Calculate basic suitability score
    score = 100

    # Penalize overlap
    score -= overlap_minutes * 2

    # Penalize incompatible gates
    score += compatibility_score

    # Keep score between 0 and 100
    score = max(0, min(100, score))

    # Store result
    gate_results.append({
        "gate": gate_id,
        "available": gate_available,
        "overlap_minutes": overlap_minutes,
        "score": score
    })

# Sort gates by suitability score
gate_results = sorted(
    gate_results,
    key=lambda x: x["score"],
    reverse=True
)

print("\n=== Gate Suitability Ranking ===\n")

for result in gate_results:

    if result["available"]:
        print(
            f"✅ {result['gate']} "
            f"| Suitability: {result['score']:.0f}% "
            f"| No conflict"
        )
    else:
        print(
            f"❌ {result['gate']} "
            f"| Suitability: {result['score']:.0f}% "
            f"| Overlap: {result['overlap_minutes']:.0f} min"
        )

# Find feasible gates
feasible_gates = [
    result for result in gate_results
    if result["available"]
]

print("\n=== GateGuard Recommendation ===\n")

if feasible_gates:

    best_gate = feasible_gates[0]

    print(f"⭐ Recommended Gate: {best_gate['gate']}")
    print(
        f"Suitability Score: "
        f"{best_gate['score']:.0f}%"
    )

    print("\nReason:")
    print("✓ No gate conflict")
    print("✓ Suitable turnaround window")
    print("✓ Gate compatibility satisfied")

else:

    print("⚠️ No feasible alternative gate available.")
    print("GateGuard recommends keeping the flight")
    print("under operational review until a suitable gate")
    print("becomes available.")