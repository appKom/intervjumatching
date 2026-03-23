from mip_matching.Committee import Committee
from mip_matching.Applicant import Applicant
import mip

from datetime import timedelta, time
from itertools import combinations

from mip_matching.types import Matching, MeetingMatch
from mip_matching.utils import subtract_time


# Hvor stort buffer man ønsker å ha mellom intervjuene
APPLICANT_BUFFER_LENGTH = timedelta(minutes=15)

# Når på dagen man helst vil ha intervjuene rundt
CLUSTERING_TIME_BASELINE = time(12, 00)
MAX_SCALE_CLUSTERING_TIME = timedelta(seconds=43200)

# En liste med alle sekundærmål-vekter.
# Hver vekt bestemmer hvor mye det tilhørende sekundærmålet påvirker optimeringen.
# Høyere vekt = sterkere preferanse for det målet.

# n^2*x + n*x + h, der n er antall intervjuer, x er en konstant.
def calculate_secondary_objective_weights(num_interviews: int) -> dict[str, float]:
    # Vekten for clustering øker kvadratisk med antall intervjuer, for å prioritere det mer når det er mange intervjuer.
    clustering_weight = 0.001 * (num_interviews ** 2)

    # Vekten for spredning over perioden øker lineært med antall intervjuer, for å sikre at det fortsatt har en betydelig effekt.
    firstDay_weight = 0.001 * num_interviews

    return {
        "clustering": clustering_weight,
        "first_day": firstDay_weight
    }


def match_meetings(applicants: set[Applicant], committees: set[Committee]) -> MeetingMatch:
    """Matches meetings and returns a MeetingMatch-object"""
    model = mip.Model(sense=mip.MAXIMIZE)

    m: dict[Matching, mip.Var] = {}


    # Lager alle maksimeringsvariabler
    for applicant in applicants:
        for committee in applicant.get_committees():
            for interval in applicant.get_fitting_committee_slots(committee):
                for room in committee.get_rooms(interval):
                    m[(applicant, committee, interval, room)] = model.add_var(
                        var_type=mip.BINARY, name=f"({applicant}, {committee}, {interval}, {room})")

    # Legger inn begrensninger for at en komité kun kan ha antall møter i et slot lik kapasiteten.
    for committee in committees:
        for interval, capacity in committee.get_intervals_and_capacities():
            model += mip.xsum(m[(applicant, committee, interval, room)]
                              for applicant in committee.get_applicants()
                              for room in committee.get_rooms(interval)
                              if (applicant, committee, interval, room) in m
                              # type: ignore
                              ) <= capacity

    # Legger inn begrensninger for at en person kun har ett intervju med hver komité
    for applicant in applicants:
        for committee in applicant.get_committees():
            model += mip.xsum(m[(applicant, committee, interval, room)]
                              for interval in applicant.get_fitting_committee_slots(committee)
                              for room in committee.get_rooms(interval)
                              # type: ignore
                              ) <= 1
    # Legger inn begrensninger for at en søker ikke kan ha overlappende intervjutider
    # og minst har et buffer mellom hvert intervju som angitt
    for applicant in applicants:
        # Grupper variabler per unikt (komité, intervall) — rom er irrelevant for overlap
        unique_slots: dict[tuple, list[mip.Var]] = {}
        for slot in m.keys():
            if slot[0] == applicant:
                key = (slot[1], slot[2])  # (committee, interval)
                if key not in unique_slots:
                    unique_slots[key] = []
                unique_slots[key].append(m[slot])

        slot_keys = list(unique_slots.keys())
        for i, key_a in enumerate(slot_keys):
            for key_b in slot_keys[i + 1:]:
                interval_a = key_a[1]
                interval_b = key_b[1]
                if interval_a.intersects(interval_b) or interval_a.is_within_distance(interval_b, APPLICANT_BUFFER_LENGTH):
                    # Sum av alle rom-variabler for begge slots <= 1
                    model += mip.xsum(unique_slots[key_a]) + mip.xsum(unique_slots[key_b]) <= 1  # type: ignore
        
    SECONDARY_OBJECTIVE_WEIGHTS = calculate_secondary_objective_weights(model.num_cols);

    # Legger til sekundærmål om at man ønsker å sentrere intervjuer rundt CLUSTERING_TIME_BASELINE
    # og at man foretrekker intervjuer senere i søknadsperioden
    secondary_penalties = []

    # Finn den tidligste og seneste datoen blant alle intervjuer for å normalisere
    all_dates = [interval.start for (_, _, interval, _) in m.keys()]
    min_date = min(all_dates)

    for name, variable in m.items():
        applicant, committee, interval, room = name

        # Sekundærmål 1: Clustering rundt CLUSTERING_TIME_BASELINE
        if interval.start.time() < CLUSTERING_TIME_BASELINE:
            relative_distance_from_baseline = subtract_time(CLUSTERING_TIME_BASELINE,
                                                            interval.end.time()) / MAX_SCALE_CLUSTERING_TIME
        else:
            relative_distance_from_baseline = subtract_time(interval.start.time(),
                                                            CLUSTERING_TIME_BASELINE) / MAX_SCALE_CLUSTERING_TIME

        secondary_penalties.append(
            SECONDARY_OBJECTIVE_WEIGHTS["clustering"] * relative_distance_from_baseline * variable)  # type: ignore

        # Sekundærmål 2: Foretrekk intervjuer senere i perioden
        # Gir lavere straff jo senere i perioden intervjuet er
        if interval.start.date() == min_date.date():
            secondary_penalties.append(
                SECONDARY_OBJECTIVE_WEIGHTS["first_day"] * variable) # type: ignore
            
    # Setter mål til å være maksimering av antall møter
    # med sekundærmål om å samle intervjuene og foretrekke senere datoer
    model.objective = mip.maximize(
        mip.xsum(m.values()) - mip.xsum(secondary_penalties))

    # Kjør optimeringen
    solver_status = model.optimize()

    # Få de faktiske møtetidene
    total_matched_meetings: int = 0
    matchings: list = []
    for name, variable in m.items():
        if variable.x:
            total_matched_meetings += 1
            matchings.append(name)

    total_wanted_meetings = sum(
        len(applicant.get_committees()) for applicant in applicants)
    
    print(f"Matched {total_matched_meetings} out of {total_wanted_meetings} wanted meetings.")
    print(model.num_cols)

    match_object: MeetingMatch = {
        "solver_status": solver_status,
        "matched_meetings": total_matched_meetings,
        "total_wanted_meetings": total_wanted_meetings,
        "matchings": matchings,
    }

    return match_object
