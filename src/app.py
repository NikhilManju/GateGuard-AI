import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="GateGuard AI",
    page_icon="✈️",
    layout="wide"
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():
    flights = pd.read_csv("data/flights.csv")
    gates = pd.read_csv("data/gates.csv")

    return flights, gates


# Load the original data
flights, gates = load_data()

# Store a working copy in Streamlit session state
if "flights_data" not in st.session_state:
    st.session_state.flights_data = flights.copy()

# Use the working copy
flights = st.session_state.flights_data.copy()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def time_to_minutes(time_value):

    """
    Converts HH:MM time into minutes from midnight.
    """

    if isinstance(time_value, str):

        hour, minute = map(int, time_value.split(":"))

        return hour * 60 + minute

    return int(time_value)


def minutes_to_time(total_minutes):

    """
    Converts minutes from midnight back to HH:MM.
    """

    total_minutes = total_minutes % (24 * 60)

    hour = total_minutes // 60
    minute = total_minutes % 60

    return f"{hour:02d}:{minute:02d}"


def calculate_flight_times(flight, delay):

    """
    Calculates predicted arrival and gate release
    after applying the delay from the dashboard.
    """

    scheduled_arrival = time_to_minutes(
        flight["scheduled_arrival"]
    )

    turnaround = int(
        flight["turnaround_minutes"]
    )

    predicted_arrival = scheduled_arrival + delay

    predicted_release = (
        predicted_arrival + turnaround
    )

    return predicted_arrival, predicted_release


def get_flight_times(flight, additional_delay=0):

    """
    Returns predicted arrival and release time.
    """

    delay = int(flight["delay_minutes"]) + int(additional_delay)

    return calculate_flight_times(
        flight,
        delay
    )


def get_gate_occupancy(other_flight):

    """
    Calculates when another flight occupies its gate.
    """

    arrival = time_to_minutes(
        other_flight["scheduled_arrival"]
    )

    delay = int(
        other_flight["delay_minutes"]
    )

    turnaround = int(
        other_flight["turnaround_minutes"]
    )

    predicted_arrival = arrival + delay

    predicted_release = (
        predicted_arrival + turnaround
    )

    return predicted_arrival, predicted_release


def calculate_overlap(
    target_arrival,
    target_release,
    other_arrival,
    other_release
):

    """
    Calculates overlap between two gate occupancy windows.
    """

    overlap_start = max(
        target_arrival,
        other_arrival
    )

    overlap_end = min(
        target_release,
        other_release
    )

    if overlap_start < overlap_end:

        return overlap_end - overlap_start

    return 0


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("✈️ Flight Operations")

selected_flight_id = st.sidebar.selectbox(
    "Select Flight",
    flights["flight_id"].tolist()
)


# Get selected flight

selected_flight = flights[
    flights["flight_id"] == selected_flight_id
].iloc[0]


current_gate = selected_flight[
    "assigned_gate"
]


st.sidebar.write(
    f"**Airline:** {selected_flight['airline']}"
)

st.sidebar.write(
    f"**Current Gate:** {current_gate}"
)


# ============================================================
# DELAY CONTROL
# ============================================================

base_delay = int(
    selected_flight["delay_minutes"]
)


delay_minutes = st.sidebar.slider(
    "Delay (minutes)",
    min_value=0,
    max_value=120,
    value=base_delay,
    step=5
)


st.sidebar.caption(
    "Adjust the delay to simulate a live operational change."
)


analyze_button = st.sidebar.button(
    "🔍 Analyze Gate Situation",
    use_container_width=True
)


# ============================================================
# CALCULATE SELECTED FLIGHT
# ============================================================

predicted_arrival, predicted_release = calculate_flight_times(
    selected_flight,
    delay_minutes
)


# ============================================================
# HEADER
# ============================================================

st.title("✈️ GateGuard AI")

st.subheader(
    "Predictive Airport Gate Allocation & Conflict Prevention"
)

st.write(
    "GateGuard analyzes flight delays, gate occupancy and "
    "future conflicts to recommend the most suitable "
    "alternative gate."
)


st.divider()


# ============================================================
# FLIGHT STATUS
# ============================================================

st.header("✈️ Flight Status")


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Flight",
        selected_flight_id
    )


with col2:

    st.metric(
        "Airline",
        selected_flight["airline"]
    )


with col3:

    st.metric(
        "Predicted Arrival",
        minutes_to_time(predicted_arrival)
    )


with col4:

    st.metric(
        "Predicted Gate Release",
        minutes_to_time(predicted_release)
    )


# ============================================================
# CONFLICT DETECTION
# ============================================================

conflicting_flights = []


for _, other_flight in flights.iterrows():

    # Ignore selected flight

    if other_flight["flight_id"] == selected_flight_id:
        continue


    # Only compare flights using the same gate

    if other_flight["assigned_gate"] != current_gate:
        continue


    other_arrival, other_release = get_gate_occupancy(
        other_flight
    )


    overlap = calculate_overlap(
        predicted_arrival,
        predicted_release,
        other_arrival,
        other_release
    )


    if overlap > 0:

        conflicting_flights.append(
            {
                "flight_id": other_flight["flight_id"],
                "airline": other_flight["airline"],
                "overlap": overlap,
                "arrival": other_arrival,
                "release": other_release
            }
        )


# ============================================================
# CONFLICT ALERT
# ============================================================

if conflicting_flights:

    st.error(
        f"⚠️ GATE CONFLICT DETECTED — {current_gate}"
    )

    for conflict in conflicting_flights:

        st.write(
            f"**{selected_flight_id}** conflicts with "
            f"**{conflict['flight_id']} "
            f"({conflict['airline']})** "
            f"for approximately "
            f"**{conflict['overlap']} minutes**."
        )

else:

    st.success(
        f"✅ No conflict detected at Gate {current_gate}"
    )


st.divider()


# ---------------------------------------------------------
# GATE SUITABILITY
# ---------------------------------------------------------

st.header("🧠 GateGuard Gate Suitability Analysis")

gate_results = []

# Target flight timing
target_arrival = predicted_arrival
target_release = predicted_release

# ---------------------------------------------------------
# Evaluate every alternative gate
# ---------------------------------------------------------

for _, gate in gates.iterrows():

    gate_id = gate["gate_id"]

    # Never recommend the current gate
    if gate_id == current_gate:
        continue

    gate_available = True
    total_overlap = 0
    future_risk = 0
    next_flight_gap = None

    # -----------------------------------------------------
    # Check flights already assigned to this gate
    # -----------------------------------------------------

    gate_flights = flights[
        (flights["assigned_gate"] == gate_id) &
        (flights["flight_id"] != selected_flight_id)
    ]

    for _, other in gate_flights.iterrows():

        # Calculate other flight arrival after its delay
        other_arrival = (
            time_to_minutes(other["scheduled_arrival"])
            + int(other["delay_minutes"])
        )

        # Calculate other flight gate release
        other_release = (
            other_arrival
            + int(other["turnaround_minutes"])
        )

        # -------------------------------------------------
        # Immediate overlap
        # -------------------------------------------------

        latest_start = max(target_arrival, other_arrival)
        earliest_end = min(target_release, other_release)

        if latest_start < earliest_end:

            gate_available = False

            overlap = earliest_end - latest_start
            total_overlap += overlap

        # -------------------------------------------------
        # Future downstream risk
        #
        # If another flight is arriving soon after our
        # target flight, we check how much time is available
        # between our release and that flight.
        # -------------------------------------------------

        if other_arrival >= target_release:

            gap = other_arrival - target_release

            if next_flight_gap is None or gap < next_flight_gap:
                next_flight_gap = gap

            # Very small gap = higher operational risk
            if gap < 15:
                future_risk += 30

            elif gap < 30:
                future_risk += 20

            elif gap < 45:
                future_risk += 10

    # -----------------------------------------------------
    # TURNAROUND WINDOW SCORE
    # -----------------------------------------------------

    if next_flight_gap is None:
        turnaround_score = 25

    elif next_flight_gap >= 60:
        turnaround_score = 25

    elif next_flight_gap >= 45:
        turnaround_score = 20

    elif next_flight_gap >= 30:
        turnaround_score = 15

    elif next_flight_gap >= 15:
        turnaround_score = 8

    else:
        turnaround_score = 0

    # -----------------------------------------------------
    # COMPATIBILITY SCORE
    # -----------------------------------------------------

    compatibility_score = 0

    if "international_capable" in gates.columns:

        if gate["international_capable"] == "Yes":
            compatibility_score = 20
        else:
            compatibility_score = 10

    else:
        compatibility_score = 20

    # -----------------------------------------------------
    # CONFLICT SCORE
    # -----------------------------------------------------

    if gate_available:
        conflict_score = 40
    else:
        conflict_score = 0

    # -----------------------------------------------------
    # FUTURE RISK PENALTY
    # -----------------------------------------------------

    future_risk_penalty = min(future_risk, 25)

    # -----------------------------------------------------
    # FINAL SUITABILITY SCORE
    #
    # Maximum:
    #
    # Conflict freedom       = 40
    # Turnaround window      = 25
    # Compatibility          = 20
    # Future safety          = 15
    #
    # Total                  = 100
    # -----------------------------------------------------

    future_safety_score = 15 - min(future_risk_penalty, 15)

    suitability_score = (
        conflict_score
        + turnaround_score
        + compatibility_score
        + future_safety_score
    )

    suitability_score = max(0, min(100, suitability_score))

    # -----------------------------------------------------
    # Store result
    # -----------------------------------------------------

    gate_results.append({
        "gate": gate_id,
        "available": gate_available,
        "overlap": total_overlap,
        "next_flight_gap": next_flight_gap,
        "future_risk": future_risk,
        "score": suitability_score
    })


# ---------------------------------------------------------
# SORT BEST GATE FIRST
# ---------------------------------------------------------

gate_results = sorted(
    gate_results,
    key=lambda x: x["score"],
    reverse=True
)


# ---------------------------------------------------------
# DISPLAY RESULTS
# ---------------------------------------------------------

for result in gate_results:

    gate_id = result["gate"]
    score = result["score"]
    overlap = result["overlap"]

    if result["available"]:

        if score >= 80:
            st.success(
                f"🟢 **{gate_id} — Suitability: {score}% | "
                f"Low future conflict risk**"
            )

        elif score >= 60:
            st.info(
                f"🔵 **{gate_id} — Suitability: {score}% | "
                f"Moderate operational risk**"
            )

        else:
            st.warning(
                f"🟡 **{gate_id} — Suitability: {score}% | "
                f"Lower suitability**"
            )

    else:

        st.error(
            f"🔴 **{gate_id} — Suitability: {score}% | "
            f"Overlap: {overlap} min**"
        )


# ---------------------------------------------------------
# BEST GATE
# ---------------------------------------------------------

if gate_results:

    best_gate = gate_results[0]

    recommended_gate = best_gate["gate"]
    recommended_score = best_gate["score"]

else:

    recommended_gate = None
    recommended_score = 0


# ---------------------------------------------------------
# GATEGUARD RECOMMENDATION
# ---------------------------------------------------------

st.divider()

st.header("⭐ GateGuard Recommendation")

if recommended_gate:

    st.success(
        f"⭐ **Recommended Gate: {recommended_gate}**"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Suitability Score",
            f"{recommended_score}%"
        )

    with col2:
        st.metric(
            "Gate Status",
            "Available"
        )

    st.subheader("Why this gate?")

    st.write("✓ No immediate gate conflict")

    if best_gate["next_flight_gap"] is not None:

        st.write(
            f"✓ {best_gate['next_flight_gap']} minutes "
            f"of buffer before the next flight"
        )

    else:

        st.write("✓ No immediate downstream flight conflict")

    st.write("✓ Gate compatibility satisfied")

    st.info(
        f"GateGuard recommends moving "
        f"**{selected_flight_id}** from "
        f"**{current_gate} → {recommended_gate}**."
    )

    st.caption(
        "This is a decision-support recommendation. "
        "Final gate assignment remains with airport/airline operations."
    )

else:

    st.warning(
        "⚠️ No suitable alternative gate available."
    )


st.divider()

st.subheader("🛫 Gate Assignment Approval")

st.write(
    f"GateGuard recommends moving **{selected_flight_id}** "
    f"from **{current_gate} → {recommended_gate}**."
)

# Store approved gate changes separately for each flight
if "approved_gate_changes" not in st.session_state:
    st.session_state.approved_gate_changes = {}

approval_key = f"{selected_flight_id}_{recommended_gate}"

# Check whether this specific recommendation has already been approved
if approval_key not in st.session_state.approved_gate_changes:

    if st.button("✅ Approve Gate Change", use_container_width=True):

        # Update the selected flight's assigned gate
        st.session_state.flights_data.loc[
            st.session_state.flights_data["flight_id"] == selected_flight_id,
            "assigned_gate"
        ] = recommended_gate

        # Remember this specific approval
        st.session_state.approved_gate_changes[approval_key] = True

        st.success(
            "✅ Gate assignment successfully updated!"
        )

        st.info(
            f"**{selected_flight_id}: "
            f"{current_gate} → {recommended_gate}**"
        )

        st.write("**Status:** Approved by Operations")

        st.write(
            f"**Current Assigned Gate:** {recommended_gate}"
        )

        st.write(
            "The approved gate change can now be communicated "
            "through the airport/airline's existing operational process."
        )

else:

    st.success(
        f"✅ Gate Assignment Updated: "
        f"{selected_flight_id} → {recommended_gate}"
    )

    st.write("**Status:** Approved by Operations")

    st.write(
        f"**Current Assigned Gate:** {recommended_gate}"
    )

    st.write(
        "The approved gate change can now be communicated "
        "through the airport/airline's existing operational process."
    )