"""
Production-Level College Timetable Scheduling using a Genetic Algorithm (GA)
============================================================================

Models:
  - One division with multiple batches (labs only)
  - Theory courses → 1-hr sessions for whole division (credits = weekly sessions)
  - Lab courses   → 2-hr consecutive sessions per batch, in dedicated lab rooms

Hard Constraints:
  - No faculty double-booking at same day+slot
  - No room-time conflicts
  - Lab sessions use dedicated lab rooms only
  - Lab sessions occupy 2 consecutive slots (within the same day)
  - Each course appears at most once per day (per division / per batch)
  - All sessions scheduled

Soft Constraints:
  - At least one free slot within lunch window
  - Even session distribution across days
  - Minimize student idle gaps per day
  - Minimize faculty idle gaps per day
  - Time preference bias (morning / afternoon / evening)

GA Design:
  - Tournament selection, single-point crossover, mutation, elitism
  - Post-crossover/mutation repair to fix hard violations

Author : AI-generated (production rewrite)
Date   : 2026-03-24
"""

import random
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

# ──────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TheoryCourse:
    name: str
    faculty: str
    credits: int          # number of 1-hr sessions per week

@dataclass
class LabCourse:
    name: str
    faculty: str
    batches: List[str]    # batch names that attend this lab
    lab_room: str         # dedicated lab room name

@dataclass
class TheoryRoom:
    name: str
    capacity: int

@dataclass
class LabRoom:
    name: str
    subject: str          # maps to LabCourse.name

@dataclass
class Session:
    """A single schedulable unit expanded from a course."""
    session_id: int
    session_type: str     # "theory" | "lab"
    course_name: str
    faculty: str
    batch: Optional[str]  # None for theory (whole division)
    dedicated_room_idx: Optional[int]  # lab: must use this room index
    duration: int         # 1 for theory, 2 for lab


# ──────────────────────────────────────────────────────────────────────────────
# HELPER: TIME PREFERENCE WINDOWS
# ──────────────────────────────────────────────────────────────────────────────

def _get_preferred_slots(time_pref: str, num_slots: int) -> List[int]:
    """Return slot indices considered 'preferred' given a time preference."""
    if time_pref == "morning":
        return list(range(0, max(1, num_slots // 3)))
    elif time_pref == "afternoon":
        return list(range(num_slots // 3, max(num_slots // 3 + 1, 2 * num_slots // 3)))
    elif time_pref == "evening":
        return list(range(2 * num_slots // 3, num_slots))
    else:
        return list(range(num_slots))  # unbiased → all slots valid


# ──────────────────────────────────────────────────────────────────────────────
# MAIN GA CLASS
# ──────────────────────────────────────────────────────────────────────────────

class TimetableGA:
    def __init__(
        self,
        theory_courses: List[TheoryCourse],
        lab_courses: List[LabCourse],
        theory_rooms: List[TheoryRoom],
        lab_rooms: List[LabRoom],
        batches: List[str],
        days: List[str],
        time_slots: List[str],
        lunch_window_slots: List[int],    # slot indices that are the "lunch period"
        prefer_theory_time: str = "unbiased",
        prefer_lab_time: str = "unbiased",
        pop_size: int = 100,
        mutation_rate: float = 0.05,
        crossover_rate: float = 0.8,
        num_generations: int = 500,
        tournament_k: int = 3,
        elitism_count: int = 2,
    ):
        self.theory_courses = theory_courses
        self.lab_courses = lab_courses
        self.theory_rooms = theory_rooms
        self.lab_rooms = lab_rooms
        self.batches = batches
        self.days = days
        self.time_slots = time_slots
        self.lunch_window_slots = lunch_window_slots
        self.prefer_theory_time = prefer_theory_time
        self.prefer_lab_time = prefer_lab_time

        self.pop_size = int(pop_size)
        self.mutation_rate = float(mutation_rate)
        self.crossover_rate = float(crossover_rate)
        self.num_generations = int(num_generations)
        self.tournament_k = int(tournament_k)
        self.elitism_count = int(elitism_count)

        self.num_days = len(days)
        self.num_slots = len(time_slots)

        # Build lab room index map: name → combined_room_idx
        # All rooms in one list: theory_rooms first, then lab_rooms
        self._all_rooms_meta = []
        for tr in self.theory_rooms:
            self._all_rooms_meta.append({"name": tr.name, "is_lab": False, "capacity": tr.capacity, "subject": None})
        self._lab_room_start_idx = len(self.theory_rooms)
        for lr in self.lab_rooms:
            self._all_rooms_meta.append({"name": lr.name, "is_lab": True, "capacity": 0, "subject": lr.subject})
        self._total_rooms = len(self._all_rooms_meta)

        # Lab room name → combined index
        self._lab_room_idx: Dict[str, int] = {}
        for i, r in enumerate(self._all_rooms_meta):
            if r["is_lab"]:
                self._lab_room_idx[r["name"]] = i

        # Expand all sessions
        self.sessions: List[Session] = []
        self._expand_sessions()

        self.num_sessions = len(self.sessions)

        # Preferred slot sets
        self._theory_pref_slots = set(_get_preferred_slots(self.prefer_theory_time, self.num_slots))
        self._lab_pref_slots = set(_get_preferred_slots(self.prefer_lab_time, self.num_slots))

    # ── Session expansion ────────────────────────────────────────────────────

    def _expand_sessions(self):
        sid = 0
        for tc in self.theory_courses:
            for _ in range(tc.credits):
                self.sessions.append(Session(
                    session_id=sid,
                    session_type="theory",
                    course_name=tc.name,
                    faculty=tc.faculty,
                    batch=None,
                    dedicated_room_idx=None,
                    duration=1,
                ))
                sid += 1

        for lc in self.lab_courses:
            dedicated = self._lab_room_idx.get(lc.lab_room)
            for batch in lc.batches:
                self.sessions.append(Session(
                    session_id=sid,
                    session_type="lab",
                    course_name=lc.name,
                    faculty=lc.faculty,
                    batch=batch,
                    dedicated_room_idx=dedicated,
                    duration=2,
                ))
                sid += 1

    # ── Chromosome: List[(day_idx, slot_idx, room_idx)] ─────────────────────

    def _random_gene(self, session: Session) -> Tuple[int, int, int]:
        day = random.randint(0, self.num_days - 1)
        if session.session_type == "lab":
            # start slot must allow for 2 consecutive slots
            max_start = self.num_slots - 2
            slot = random.randint(0, max(0, max_start))
            room = session.dedicated_room_idx if session.dedicated_room_idx is not None else self._lab_room_start_idx
        else:
            slot = random.randint(0, self.num_slots - 1)
            room = random.randint(0, self._lab_room_start_idx - 1) if self._lab_room_start_idx > 0 else 0
        return (day, slot, room)

    def _create_random_chromosome(self) -> List[Tuple[int, int, int]]:
        return [self._random_gene(s) for s in self.sessions]

    def _initialize_population(self) -> List[List[Tuple[int, int, int]]]:
        return [self._repair(self._create_random_chromosome()) for _ in range(self.pop_size)]

    # ── Repair function ──────────────────────────────────────────────────────

    def _repair(self, chromosome: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
        """Fix obvious hard violations: wrong rooms, lab overflow, room conflicts."""
        ch = list(chromosome)
        used_room_slots: Dict[Tuple[int, int, int], int] = {}  # (day, slot, room) → session_idx

        for i, (day, slot, room) in enumerate(ch):
            sess = self.sessions[i]

            # 1. Fix lab room assignment
            if sess.session_type == "lab":
                if sess.dedicated_room_idx is not None:
                    room = sess.dedicated_room_idx
                elif room < self._lab_room_start_idx:
                    room = self._lab_room_start_idx  # push to first lab room

                # 2. Fix lab end-of-day overflow
                max_start = self.num_slots - 2
                if slot > max_start:
                    slot = random.randint(0, max(0, max_start))

            else:
                # 3. Theory must use theory rooms
                if room >= self._lab_room_start_idx and self._lab_room_start_idx > 0:
                    room = random.randint(0, self._lab_room_start_idx - 1)

            ch[i] = (day, slot, room)

        # 4. Resolve room-time conflicts (greedy: first-come first-served, re-slot others)
        used: Dict[Tuple[int, int, int], int] = {}
        for i, (day, slot, room) in enumerate(ch):
            sess = self.sessions[i]
            slots_used = [(day, slot, room)]
            if sess.session_type == "lab":
                slots_used.append((day, slot + 1, room))

            conflict = False
            for key in slots_used:
                if key in used:
                    conflict = True
                    break

            if conflict:
                # Re-assign randomly up to 10 tries
                for _ in range(10):
                    new_day = random.randint(0, self.num_days - 1)
                    if sess.session_type == "lab":
                        new_slot = random.randint(0, max(0, self.num_slots - 2))
                        new_room = room  # keep dedicated
                        new_keys = [(new_day, new_slot, new_room), (new_day, new_slot + 1, new_room)]
                    else:
                        new_slot = random.randint(0, self.num_slots - 1)
                        new_room = random.randint(0, max(0, self._lab_room_start_idx - 1)) if self._lab_room_start_idx > 0 else 0
                        new_keys = [(new_day, new_slot, new_room)]

                    if all(k not in used for k in new_keys):
                        for k in new_keys:
                            used[k] = i
                        ch[i] = (new_day, new_slot, new_room)
                        break
                else:
                    for k in slots_used:
                        used[k] = i
                    ch[i] = (day, slot, room)
            else:
                for k in slots_used:
                    used[k] = i

        return ch

    # ── Fitness function ─────────────────────────────────────────────────────

    def evaluate_fitness(self, chromosome: List[Tuple[int, int, int]]) -> float:
        hard_penalty = 0.0
        soft_score = 0.0

        # Tracking structures
        faculty_day_slots: Dict[str, Dict[int, List[int]]] = {}   # faculty → day → [slots]
        room_time: Dict[Tuple[int, int, int], int] = {}           # (day, slot, room) → sess_idx
        # course_day_division: (course_name, batch_or_None, day) → count
        course_day: Dict[Tuple[str, Optional[str], int], int] = {}
        # per-day slot usage for lunch check: day → set of used slots (for whole division)
        day_used_slots: Dict[int, set] = {}
        # for gap analysis: (batch_or_div, day) → sorted list of slots
        entity_day_slots: Dict[Tuple[str, int], List[int]] = {}

        for i, (day, slot, room) in enumerate(chromosome):
            sess = self.sessions[i]

            # ── Slots occupied ───────────────────────────────────────────────
            occupied = [(day, slot, room)]
            if sess.session_type == "lab":
                occupied.append((day, slot + 1, room))
                # Lab that crosses day boundary
                if slot + 1 >= self.num_slots:
                    hard_penalty += 5.0

            # ── Room-time conflict ───────────────────────────────────────────
            for key in occupied:
                if key in room_time:
                    hard_penalty += 3.0
                else:
                    room_time[key] = i

            # ── Theory using lab room or vice versa ─────────────────────────
            is_lab_room = room >= self._lab_room_start_idx
            if sess.session_type == "theory" and is_lab_room:
                hard_penalty += 2.0
            if sess.session_type == "lab":
                if sess.dedicated_room_idx is not None and room != sess.dedicated_room_idx:
                    hard_penalty += 5.0
                elif not is_lab_room:
                    hard_penalty += 3.0

            # ── Faculty conflict ─────────────────────────────────────────────
            fac = sess.faculty
            if fac not in faculty_day_slots:
                faculty_day_slots[fac] = {}
            if day not in faculty_day_slots[fac]:
                faculty_day_slots[fac][day] = []
            for s in (range(slot, slot + sess.duration)):
                if s in faculty_day_slots[fac][day]:
                    hard_penalty += 3.0
                faculty_day_slots[fac][day].append(s)

            # ── Same course same day (per division / batch) ──────────────────
            entity = sess.batch if sess.batch else "__division__"
            cd_key = (sess.course_name, sess.batch, day)
            course_day[cd_key] = course_day.get(cd_key, 0) + 1
            if course_day[cd_key] > 1:
                hard_penalty += 4.0

            # ── Track day slot usage (for lunch window) ──────────────────────
            if day not in day_used_slots:
                day_used_slots[day] = set()
            for s in range(slot, slot + sess.duration):
                day_used_slots[day].add(s)

            # ── Track entity slots for gap analysis ──────────────────────────
            ek = (entity, day)
            if ek not in entity_day_slots:
                entity_day_slots[ek] = []
            for s in range(slot, slot + sess.duration):
                entity_day_slots[ek].append(s)

        # ── SOFT: Lunch window ────────────────────────────────────────────────
        for d in range(self.num_days):
            used = day_used_slots.get(d, set())
            free_lunch = any(s not in used for s in self.lunch_window_slots)
            if free_lunch:
                soft_score += 8.0
            else:
                soft_score -= 5.0

        # ── SOFT: Even session distribution across days ───────────────────────
        sessions_per_day = [0] * self.num_days
        for (day, slot, room), _ in zip(chromosome, self.sessions):
            sessions_per_day[day] += 1
        ideal = self.num_sessions / max(1, self.num_days)
        for count in sessions_per_day:
            deviation = abs(count - ideal)
            soft_score -= deviation * 0.5

        # ── SOFT: Minimize idle gaps per entity (student batch / faculty) ─────
        for (entity, day), slots_list in entity_day_slots.items():
            slots_list.sort()
            deduped = sorted(set(slots_list))
            for k in range(len(deduped) - 1):
                gap = deduped[k + 1] - deduped[k] - 1
                if gap > 0:
                    soft_score -= float(gap) * 1.5

        # ── SOFT: Faculty gap minimization ───────────────────────────────────
        for fac, day_map in faculty_day_slots.items():
            for day, slots_list in day_map.items():
                slots_list_sorted = sorted(set(slots_list))
                for k in range(len(slots_list_sorted) - 1):
                    gap = slots_list_sorted[k + 1] - slots_list_sorted[k] - 1
                    if gap > 0:
                        soft_score -= float(gap) * 1.0

        # ── SOFT: Time preference ─────────────────────────────────────────────
        for i, (day, slot, room) in enumerate(chromosome):
            sess = self.sessions[i]
            if sess.session_type == "theory" and slot in self._theory_pref_slots:
                soft_score += 1.5
            elif sess.session_type == "lab" and slot in self._lab_pref_slots:
                soft_score += 1.5

        # ── Combined fitness ──────────────────────────────────────────────────
        if hard_penalty == 0:
            return soft_score
        else:
            return -hard_penalty * 100.0 + soft_score * 0.01

    # ── GA operators ─────────────────────────────────────────────────────────

    def _tournament_select(self, population, fitnesses):
        indices = random.sample(range(len(population)), min(self.tournament_k, len(population)))
        best = max(indices, key=lambda i: fitnesses[i])
        return copy.deepcopy(population[best])

    def _crossover(self, p1, p2):
        if random.random() > self.crossover_rate:
            return copy.deepcopy(p1), copy.deepcopy(p2)
        if self.num_sessions <= 1:
            return copy.deepcopy(p1), copy.deepcopy(p2)
        point = random.randint(1, self.num_sessions - 1)
        c1 = p1[:point] + p2[point:]
        c2 = p2[:point] + p1[point:]
        return c1, c2

    def _mutate(self, chromosome):
        ch = list(chromosome)
        for i in range(len(ch)):
            if random.random() < self.mutation_rate:
                ch[i] = self._random_gene(self.sessions[i])
        return ch

    def _get_best(self, population, fitnesses):
        idx = max(range(len(population)), key=lambda i: fitnesses[i])
        return copy.deepcopy(population[idx]), fitnesses[idx]

    # ── Main run loop ─────────────────────────────────────────────────────────

    def run(self):
        population = self._initialize_population()
        best_overall = None
        best_overall_fit = float("-inf")
        fitness_history = []

        for gen in range(self.num_generations):
            fitnesses = [self.evaluate_fitness(ch) for ch in population]
            gen_best, gen_best_fit = self._get_best(population, fitnesses)

            if gen_best_fit > best_overall_fit:
                best_overall = gen_best
                best_overall_fit = gen_best_fit

            fitness_history.append(best_overall_fit)

            if gen % 50 == 0:
                print(f"Generation {gen:>4d} | Best fitness: {best_overall_fit:.4f}")

            if hard_penalty := self._count_hard_violations(best_overall):
                pass  # still has violations
            else:
                print(f"\n[OK] Conflict-free schedule found at generation {gen}!")
                print(f"[INFO] Soft score: {best_overall_fit:.4f}")
                break

            # Elitism
            sorted_pop = sorted(zip(population, fitnesses), key=lambda x: x[1], reverse=True)
            new_population = [copy.deepcopy(sorted_pop[k][0]) for k in range(min(self.elitism_count, len(sorted_pop)))]

            while len(new_population) < self.pop_size:
                p1 = self._tournament_select(population, fitnesses)
                p2 = self._tournament_select(population, fitnesses)
                c1, c2 = self._crossover(p1, p2)
                c1 = self._repair(self._mutate(c1))
                c2 = self._repair(self._mutate(c2))
                new_population.append(c1)
                if len(new_population) < self.pop_size:
                    new_population.append(c2)

            population = new_population

        return best_overall, best_overall_fit, fitness_history

    def _count_hard_violations(self, chromosome) -> int:
        """Count hard violations in a chromosome (0 = valid)."""
        violations = 0
        faculty_day_slots: Dict[str, Dict[int, List[int]]] = {}
        room_time: Dict[Tuple[int, int, int], int] = {}
        course_day: Dict[Tuple[str, Optional[str], int], int] = {}

        for i, (day, slot, room) in enumerate(chromosome):
            sess = self.sessions[i]
            occupied = [(day, slot, room)]
            if sess.session_type == "lab":
                if slot + 1 >= self.num_slots:
                    violations += 1
                else:
                    occupied.append((day, slot + 1, room))

            for key in occupied:
                if key in room_time:
                    violations += 1
                room_time[key] = i

            is_lab_room = room >= self._lab_room_start_idx
            if sess.session_type == "theory" and is_lab_room:
                violations += 1
            if sess.session_type == "lab":
                if sess.dedicated_room_idx is not None and room != sess.dedicated_room_idx:
                    violations += 1
                elif not is_lab_room:
                    violations += 1

            fac = sess.faculty
            if fac not in faculty_day_slots:
                faculty_day_slots[fac] = {}
            if day not in faculty_day_slots[fac]:
                faculty_day_slots[fac][day] = []
            for s in range(slot, slot + sess.duration):
                if s in faculty_day_slots[fac][day]:
                    violations += 1
                faculty_day_slots[fac][day].append(s)

            cd_key = (sess.course_name, sess.batch, day)
            course_day[cd_key] = course_day.get(cd_key, 0) + 1
            if course_day[cd_key] > 1:
                violations += 1

        return violations


# ──────────────────────────────────────────────────────────────────────────────
# API ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def run_ga_api(config_dict=None):
    if config_dict is None:
        config_dict = {}

    # ── Parse days and time_slots ──────────────────────────────────────────
    days_raw = config_dict.get("days", ["Mon", "Tue", "Wed", "Thu", "Fri"])
    slots_raw = config_dict.get("time_slots", ["8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4"])
    batches = config_dict.get("batches", ["Batch A", "Batch B"])

    # ── Theory courses ──────────────────────────────────────────────────────
    raw_theory = config_dict.get("theory_courses", [])
    theory_courses = []
    for tc in raw_theory:
        theory_courses.append(TheoryCourse(
            name=str(tc.get("name", "Theory")),
            faculty=str(tc.get("faculty", "TBD")),
            credits=int(tc.get("credits", 1)),
        ))

    # ── Lab courses ─────────────────────────────────────────────────────────
    raw_lab = config_dict.get("lab_courses", [])
    lab_courses = []
    for lc in raw_lab:
        lc_batches = lc.get("batches", batches)
        if isinstance(lc_batches, str):
            lc_batches = [b.strip() for b in lc_batches.split(",") if b.strip()]
        lab_courses.append(LabCourse(
            name=str(lc.get("name", "Lab")),
            faculty=str(lc.get("faculty", "TBD")),
            batches=lc_batches,
            lab_room=str(lc.get("lab_room", "")),
        ))

    # ── Theory rooms ────────────────────────────────────────────────────────
    raw_theory_rooms = config_dict.get("theory_rooms", [{"name": "Room 1", "capacity": 60}])
    theory_rooms = []
    for r in raw_theory_rooms:
        theory_rooms.append(TheoryRoom(name=str(r.get("name", "Room")), capacity=int(r.get("capacity", 60))))

    # ── Lab rooms ───────────────────────────────────────────────────────────
    raw_lab_rooms = config_dict.get("lab_rooms", [])
    lab_rooms = []
    for r in raw_lab_rooms:
        lab_rooms.append(LabRoom(name=str(r.get("name", "Lab Room")), subject=str(r.get("subject", ""))))

    # ── Lunch window ────────────────────────────────────────────────────────
    lunch_raw = config_dict.get("lunch_window", {})
    lunch_start_label = lunch_raw.get("start_slot", "")
    lunch_end_label = lunch_raw.get("end_slot", "")
    lunch_window_slots = []
    for idx, s in enumerate(slots_raw):
        sl = s.strip()
        if lunch_start_label and lunch_end_label:
            if sl == lunch_start_label.strip() or sl == lunch_end_label.strip():
                lunch_window_slots.append(idx)
        elif lunch_start_label and sl == lunch_start_label.strip():
            lunch_window_slots.append(idx)
    # Fallback: middle 2 slots
    if not lunch_window_slots and len(slots_raw) >= 2:
        mid = len(slots_raw) // 2
        lunch_window_slots = [mid - 1, mid]

    # ── Time preferences ────────────────────────────────────────────────────
    prefer_theory = config_dict.get("prefer_theory_time", "unbiased")
    prefer_lab    = config_dict.get("prefer_lab_time", "unbiased")

    # ── GA parameters ───────────────────────────────────────────────────────
    ga = TimetableGA(
        theory_courses=theory_courses,
        lab_courses=lab_courses,
        theory_rooms=theory_rooms,
        lab_rooms=lab_rooms,
        batches=batches,
        days=days_raw,
        time_slots=slots_raw,
        lunch_window_slots=lunch_window_slots,
        prefer_theory_time=prefer_theory,
        prefer_lab_time=prefer_lab,
        pop_size=int(config_dict.get("population_size", 100)),
        mutation_rate=float(config_dict.get("mutation_rate", 0.05)),
        crossover_rate=float(config_dict.get("crossover_rate", 0.8)),
        num_generations=int(config_dict.get("max_generations", 500)),
        tournament_k=int(config_dict.get("tournament_k", 3)),
        elitism_count=int(config_dict.get("elitism_count", 2)),
    )

    # ── Run ──────────────────────────────────────────────────────────────────
    best_chromosome, best_fitness, fitness_history = ga.run()

    violations = ga._count_hard_violations(best_chromosome)

    # ── Build schedule list ──────────────────────────────────────────────────
    schedule = []
    for i, (day, slot, room) in enumerate(best_chromosome):
        sess = ga.sessions[i]
        room_meta = ga._all_rooms_meta[room]
        end_slot = slot + sess.duration - 1
        slot_label = slots_raw[slot] if slot < len(slots_raw) else str(slot)
        end_label  = slots_raw[end_slot] if end_slot < len(slots_raw) else str(end_slot)
        time_label = f"{slot_label}–{end_label}" if sess.duration > 1 else slot_label
        schedule.append({
            "session_id":   sess.session_id,
            "type":         sess.session_type,
            "course":       sess.course_name,
            "faculty":      sess.faculty,
            "batch":        sess.batch if sess.batch else "Whole Division",
            "day":          days_raw[day],
            "day_idx":      day,
            "slot":         slot_label,
            "slot_idx":     slot,
            "end_slot":     end_label,
            "duration":     sess.duration,
            "time_label":   time_label,
            "room":         room_meta["name"],
            "is_lab_room":  room_meta["is_lab"],
        })

    # ── Build grids ───────────────────────────────────────────────────────────

    # --- By Day grid: day → slot_label → list of session dicts
    grid_by_day: Dict[str, Dict[str, List[dict]]] = {}
    for d in days_raw:
        grid_by_day[d] = {s: [] for s in slots_raw}

    for entry in schedule:
        day_label = entry["day"]
        start_idx = entry["slot_idx"]
        for offset in range(entry["duration"]):
            si = start_idx + offset
            if si < len(slots_raw):
                tsl = slots_raw[si]
                cell_entry = dict(entry)
                cell_entry["is_continuation"] = (offset > 0)
                grid_by_day[day_label][tsl].append(cell_entry)

    # --- By Room grid: room_name → day → slot → list
    grid_by_room: Dict[str, Dict[str, Dict[str, List[dict]]]] = {}
    for rm in ga._all_rooms_meta:
        grid_by_room[rm["name"]] = {d: {s: [] for s in slots_raw} for d in days_raw}
    for entry in schedule:
        rm_name = entry["room"]
        day_label = entry["day"]
        start_idx = entry["slot_idx"]
        for offset in range(entry["duration"]):
            si = start_idx + offset
            if si < len(slots_raw):
                tsl = slots_raw[si]
                cell_entry = dict(entry)
                cell_entry["is_continuation"] = (offset > 0)
                grid_by_room[rm_name][day_label][tsl].append(cell_entry)

    # --- By Batch grid: batch_name → day → slot → list
    all_entities = set()
    for sess in ga.sessions:
        all_entities.add(sess.batch if sess.batch else "Whole Division")
    grid_by_batch: Dict[str, Dict[str, Dict[str, List[dict]]]] = {}
    for entity in all_entities:
        grid_by_batch[entity] = {d: {s: [] for s in slots_raw} for d in days_raw}
    for entry in schedule:
        entity = entry["batch"]
        # Theory sessions go to "Whole Division" bucket AND all batches
        if entity == "Whole Division":
            for ent in all_entities:
                day_label = entry["day"]
                start_idx = entry["slot_idx"]
                for offset in range(entry["duration"]):
                    si = start_idx + offset
                    if si < len(slots_raw):
                        tsl = slots_raw[si]
                        cell_entry = dict(entry)
                        cell_entry["is_continuation"] = (offset > 0)
                        grid_by_batch[ent][day_label][tsl].append(cell_entry)
        else:
            day_label = entry["day"]
            start_idx = entry["slot_idx"]
            for offset in range(entry["duration"]):
                si = start_idx + offset
                if si < len(slots_raw):
                    tsl = slots_raw[si]
                    cell_entry = dict(entry)
                    cell_entry["is_continuation"] = (offset > 0)
                    grid_by_batch[entity][day_label][tsl].append(cell_entry)

    # ── Violation detail ──────────────────────────────────────────────────────
    violation_detail = _build_violation_detail(ga, best_chromosome, days_raw, slots_raw)

    return {
        "schedule":          schedule,
        "grid_by_day":       grid_by_day,
        "grid_by_room":      grid_by_room,
        "grid_by_batch":     grid_by_batch,
        "all_rooms":         [m["name"] for m in ga._all_rooms_meta],
        "theory_rooms":      [tr.name for tr in theory_rooms],
        "lab_rooms":         [lr.name for lr in lab_rooms],
        "all_batches":       sorted(all_entities),
        "days":              days_raw,
        "time_slots":        slots_raw,
        "fitness":           best_fitness,
        "violations":        violations,
        "violation_detail":  violation_detail,
        "fitness_history":   fitness_history,
        "generations_run":   len(fitness_history),
        "total_sessions":    ga.num_sessions,
        "theory_sessions":   sum(1 for s in ga.sessions if s.session_type == "theory"),
        "lab_sessions":      sum(1 for s in ga.sessions if s.session_type == "lab"),
        "config": {
            "population_size":   ga.pop_size,
            "mutation_rate":     ga.mutation_rate,
            "crossover_rate":    ga.crossover_rate,
            "max_generations":   ga.num_generations,
            "elitism_count":     ga.elitism_count,
            "tournament_k":      ga.tournament_k,
            "num_theory_rooms":  len(theory_rooms),
            "num_lab_rooms":     len(lab_rooms),
            "num_days":          len(days_raw),
            "num_slots":         len(slots_raw),
            "prefer_theory_time": prefer_theory,
            "prefer_lab_time":    prefer_lab,
            "lunch_window":      [slots_raw[s] for s in ga.lunch_window_slots if s < len(slots_raw)],
        },
    }


def _build_violation_detail(ga: TimetableGA, chromosome, days_raw, slots_raw) -> List[str]:
    """Return human-readable list of hard violations found."""
    msgs = []
    faculty_day_slots: Dict[str, Dict[int, List[int]]] = {}
    room_time: Dict[Tuple[int, int, int], int] = {}
    course_day: Dict[Tuple[str, Optional[str], int], int] = {}

    for i, (day, slot, room) in enumerate(chromosome):
        sess = ga.sessions[i]
        day_label  = days_raw[day] if day < len(days_raw) else str(day)
        slot_label = slots_raw[slot] if slot < len(slots_raw) else str(slot)

        if sess.session_type == "lab" and slot + 1 >= ga.num_slots:
            msgs.append(f"Lab '{sess.course_name}' ({sess.batch}) on {day_label} @ {slot_label} overflows day boundary.")

        occupied = [(day, slot, room)]
        if sess.session_type == "lab" and slot + 1 < ga.num_slots:
            occupied.append((day, slot + 1, room))

        for key in occupied:
            if key in room_time:
                other_sess = ga.sessions[room_time[key]]
                rm_name = ga._all_rooms_meta[key[2]]["name"] if key[2] < len(ga._all_rooms_meta) else str(key[2])
                msgs.append(f"Room conflict: '{sess.course_name}' and '{other_sess.course_name}' both in {rm_name} on {day_label} @ {slots_raw[key[1]] if key[1] < len(slots_raw) else key[1]}.")
            room_time[key] = i

        is_lab_room = room >= ga._lab_room_start_idx
        if sess.session_type == "theory" and is_lab_room:
            msgs.append(f"Theory '{sess.course_name}' placed in lab room on {day_label} @ {slot_label}.")
        if sess.session_type == "lab" and sess.dedicated_room_idx is not None and room != sess.dedicated_room_idx:
            msgs.append(f"Lab '{sess.course_name}' ({sess.batch}) not in its dedicated room on {day_label} @ {slot_label}.")

        fac = sess.faculty
        if fac not in faculty_day_slots:
            faculty_day_slots[fac] = {}
        if day not in faculty_day_slots[fac]:
            faculty_day_slots[fac][day] = []
        for s in range(slot, slot + sess.duration):
            if s in faculty_day_slots[fac][day]:
                msgs.append(f"Faculty conflict: '{fac}' double-booked on {day_label} @ slot {s}.")
            faculty_day_slots[fac][day].append(s)

        cd_key = (sess.course_name, sess.batch, day)
        course_day[cd_key] = course_day.get(cd_key, 0) + 1
        if course_day[cd_key] > 1:
            entity = sess.batch if sess.batch else "Whole Division"
            msgs.append(f"Repeat: '{sess.course_name}' for '{entity}' appears more than once on {day_label}.")

    return msgs[:30]  # cap at 30 messages


# ──────────────────────────────────────────────────────────────────────────────
# LEGACY ENTRY POINT (kept for CLI usage)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    SAMPLE = {
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "time_slots": ["8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4"],
        "batches": ["Batch A", "Batch B"],
        "theory_courses": [
            {"name": "Mathematics",   "faculty": "Prof. Smith",   "credits": 3},
            {"name": "Physics",       "faculty": "Prof. Johnson", "credits": 2},
            {"name": "Data Structures","faculty": "Prof. Davis",  "credits": 3},
        ],
        "lab_courses": [
            {
                "name":    "Physics Lab",
                "faculty": "Prof. Johnson",
                "batches": ["Batch A", "Batch B"],
                "lab_room": "Physics Lab Room",
            },
            {
                "name":    "CS Lab",
                "faculty": "Prof. Davis",
                "batches": ["Batch A", "Batch B"],
                "lab_room": "Computer Lab",
            },
        ],
        "theory_rooms": [
            {"name": "Lecture Hall A", "capacity": 60},
            {"name": "Lecture Hall B", "capacity": 60},
        ],
        "lab_rooms": [
            {"name": "Physics Lab Room", "subject": "Physics Lab"},
            {"name": "Computer Lab",     "subject": "CS Lab"},
        ],
        "lunch_window":       {"start_slot": "12-1", "end_slot": "1-2"},
        "prefer_theory_time": "morning",
        "prefer_lab_time":    "afternoon",
        "population_size":    80,
        "max_generations":    300,
    }

    result = run_ga_api(SAMPLE)
    print(f"\nFitness: {result['fitness']:.4f}  |  Violations: {result['violations']}")
    print(f"Theory sessions: {result['theory_sessions']}  |  Lab sessions: {result['lab_sessions']}")
    if result["violation_detail"]:
        print("\nViolation details:")
        for v in result["violation_detail"]:
            print(f"  ✗ {v}")
    else:
        print("\n✓ No hard constraint violations!")
