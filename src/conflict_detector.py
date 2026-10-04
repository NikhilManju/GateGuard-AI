import pandas as pd

# Load flight data
flights = pd.read_csv("data/flights.csv")

# Convert time columns into time values
flights["scheduled_arrival"] = pd.to_datetime(
    flights["scheduled_arrival"],
    format="%H:%M"
)

flights["scheduled_departure"] = pd.to_datetime(
    flights["scheduled_departure"],
    format="%H:%M"
)

# Calculate the planned gate release time
flights["planned_gate_release"] = (
    flights["scheduled_arrival"]
    + pd.to_timedelta(flights["turnaround_minutes"], unit="m")
)

# Calculate predicted arrival time after delay
flights["predicted_arrival"] = (
    flights["scheduled_arrival"]
    + pd.to_timedelta(flights["delay_minutes"], unit="m")
)

# Calculate predicted gate release time after delay
flights["predicted_gate_release"] = (
    flights["planned_gate_release"]
    + pd.to_timedelta(flights["delay_minutes"], unit="m")
)

print("\n--- GateGuard Flight Analysis ---\n")

for _, flight in flights.iterrows():

    print(f"Flight: {flight['flight_id']}")
    print(f"Airline: {flight['airline']}")
    print(f"Gate: {flight['assigned_gate']}")
    print(f"Predicted Arrival: {flight['predicted_arrival'].strftime('%H:%M')}")
    print(
        f"Predicted Gate Release: "
        f"{flight['predicted_gate_release'].strftime('%H:%M')}"
    )
    print()
# Check for potential gate conflicts
print("\n--- Gate Conflict Detection ---\n")

for gate in flights["assigned_gate"].unique():

    gate_flights = flights[
        flights["assigned_gate"] == gate
    ].sort_values("predicted_arrival")

    for i in range(len(gate_flights) - 1):

        current_flight = gate_flights.iloc[i]
        next_flight = gate_flights.iloc[i + 1]

        if (
            next_flight["predicted_arrival"]
            < current_flight["predicted_gate_release"]
        ):
            print(
                f"⚠️ CONFLICT DETECTED at {gate}: "
                f"{current_flight['flight_id']} → "
                f"{next_flight['flight_id']}"
            )
        else:
            print(
                f"✅ {gate}: "
                f"{current_flight['flight_id']} → "
                f"{next_flight['flight_id']} is safe"
            )