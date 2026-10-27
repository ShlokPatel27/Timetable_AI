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

import nlp_engine


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
        nlp_constraints: Optional[List[Dict[str, Any]]] = None,
        seed_chromosome: Optional[List[Tuple[int, int, int]]] = None,
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
        self.nlp_constraints = nlp_constraints or []
        self.seed_chromosome = seed_chromosome

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
        pop = []
        if self.seed_chromosome and len(self.seed_chromosome) == self.num_sessions:
            pop.append(self._repair(list(self.seed_chromosome)))
            for _ in range(max(1, self.pop_size // 3)):
                mutated = self._mutate(self.seed_chromosome)
                pop.append(self._repair(mutated))
        while len(pop) < self.pop_size:
            pop.append(self._repair(self._create_random_chromosome()))
        return pop

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
                # Re-assign randomly up to 15 tries
                for _ in range(15):
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

        # 5. Resolve division-level theory slot conflicts (strictly 1 theory session per day+slot)
        theory_occupied_slots: Dict[Tuple[int, int], int] = {}
        for i, (day, slot, room) in enumerate(ch):
            sess = self.sessions[i]
            if sess.session_type != "theory":
                continue
            ds_key = (day, slot)
            if ds_key in theory_occupied_slots:
                # Conflict: find a slot with no other theory session
                all_combos = [(d, s) for d in range(self.num_days) for s in range(self.num_slots)]
                random.shuffle(all_combos)
                moved = False
                for new_d, new_s in all_combos:
                    new_ds = (new_d, new_s)
                    if new_ds not in theory_occupied_slots:
                        # Find an available theory room for this day+slot
                        avail_rooms = [
                            r for r in range(max(1, self._lab_room_start_idx))
                            if (new_d, new_s, r) not in used
                        ]
                        if avail_rooms:
                            new_r = random.choice(avail_rooms)
                            # Remove old used key
                            used.pop((day, slot, room), None)
                            used[(new_d, new_s, new_r)] = i
                            ch[i] = (new_d, new_s, new_r)
                            theory_occupied_slots[new_ds] = i
                            moved = True
                            break
                if not moved:
                    theory_occupied_slots[ds_key] = i
            else:
                theory_occupied_slots[ds_key] = i

        # 6. Resolve student batch overlaps (no batch can have 2 sessions in the same slot)
        batch_slots: Dict[str, Dict[Tuple[int, int], int]] = {b: {} for b in self.batches}
        for i, (day, slot, room) in enumerate(ch):
            sess = self.sessions[i]
            assigned = self.batches if sess.session_type == "theory" else ([sess.batch] if sess.batch else self.batches)
            has_conflict = False
            for b in assigned:
                for s in range(slot, slot + sess.duration):
                    if (day, s) in batch_slots.get(b, {}):
                        has_conflict = True
                        break
                if has_conflict:
                    break

            if has_conflict:
                max_s = self.num_slots - (1 if sess.session_type == "lab" else 0)
                all_combos = [(d, s) for d in range(self.num_days) for s in range(max_s)]
                random.shuffle(all_combos)
                for new_d, new_s in all_combos:
                    dur_slots = list(range(new_s, new_s + sess.duration))
                    # Check batch availability
                    if any((new_d, s) in batch_slots.get(b, {}) for b in assigned for s in dur_slots):
                        continue
                    # Check room availability
                    if sess.session_type == "lab":
                        target_room = sess.dedicated_room_idx if sess.dedicated_room_idx is not None else self._lab_room_start_idx
                        if all((new_d, s, target_room) not in used for s in dur_slots):
                            for s in range(slot, slot + sess.duration):
                                used.pop((day, s, room), None)
                            for s in dur_slots:
                                used[(new_d, s, target_room)] = i
                            ch[i] = (new_d, new_s, target_room)
                            day, slot, room = new_d, new_s, target_room
                            break
                    else:
                        avail = [r for r in range(max(1, self._lab_room_start_idx)) if (new_d, new_s, r) not in used]
                        if avail:
                            target_room = random.choice(avail)
                            used.pop((day, slot, room), None)
                            used[(new_d, new_s, target_room)] = i
                            ch[i] = (new_d, new_s, target_room)
                            day, slot, room = new_d, new_s, target_room
                            break

            for b in assigned:
                if b not in batch_slots:
                    batch_slots[b] = {}
                for s in range(slot, slot + sess.duration):
                    batch_slots[b][(day, s)] = i

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
        # Division-level slot: only one theory session per (day, slot) regardless of room
        division_slot: Dict[Tuple[int, int], int] = {}  # (day, slot) → sess_idx
        # Batch-level slot: no student batch can have 2 sessions at the same (day, slot)
        batch_day_slots: Dict[str, Dict[Tuple[int, int], int]] = {b: {} for b in self.batches}

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

            # ── Division-level theory slot conflict ──────────────────────
            if sess.session_type == "theory":
                ds_key = (day, slot)
                if ds_key in division_slot:
                    hard_penalty += 5.0  # two theory classes at same time = impossible for students
                else:
                    division_slot[ds_key] = i

            # ── Student batch conflict (theory occupies all batches; lab occupies assigned batch) ──
            assigned_batches = self.batches if sess.session_type == "theory" else ([sess.batch] if sess.batch else self.batches)
            for b in assigned_batches:
                if b not in batch_day_slots:
                    batch_day_slots[b] = {}
                for s in range(slot, slot + sess.duration):
                    b_key = (day, s)
                    if b_key in batch_day_slots[b]:
                        hard_penalty += 6.0  # students cannot be in two classes at once
                    else:
                        batch_day_slots[b][b_key] = i

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

        # ── SOFT: Natural Language Constraints (NLP Engine) ───────────────────
        if self.nlp_constraints:
            morning_slots = set(range(0, max(1, self.num_slots // 2)))
            afternoon_slots = set(range(max(1, self.num_slots // 2), self.num_slots))

            for c in self.nlp_constraints:
                intent = c.get("intent", "")
                polarity = c.get("polarity", "POSITIVE")
                c_faculty = c.get("faculty")
                c_course = c.get("course")
                c_room = c.get("room")
                c_batch = c.get("batch")
                c_days = set(c.get("days", []))
                c_period = c.get("period")
                c_slot = c.get("specific_slot")

                # Track if at least one session satisfies target placement for MOVE_SESSION
                target_placed = False

                for i, (day, slot, room_idx) in enumerate(chromosome):
                    sess = self.sessions[i]
                    day_name = self.days[day] if day < len(self.days) else ""
                    room_name = self._all_rooms_meta[room_idx]["name"] if room_idx < len(self._all_rooms_meta) else ""

                    fac_match = (not c_faculty) or (c_faculty.lower() in sess.faculty.lower())
                    crs_match = (not c_course) or (c_course.lower() in sess.course_name.lower())
                    bch_match = (not c_batch) or (sess.batch and c_batch.lower() in sess.batch.lower())

                    # Targeted move / specific placement
                    if crs_match and (c_faculty is None or fac_match) and (c_course or c_faculty):
                        match_day = (not c_days) or (day_name in c_days)
                        match_slot = (
                            (c_period == "morning" and slot in morning_slots) or
                            (c_period == "afternoon" and slot in afternoon_slots) or
                            (c_slot and slot < len(self.time_slots) and (self.time_slots[slot] == c_slot or c_slot in self.time_slots[slot])) or
                            (not c_period and not c_slot)
                        )
                        match_room = (not c_room) or (c_room.lower() in room_name.lower())

                        if match_day and match_slot and match_room:
                            if polarity == "POSITIVE":
                                target_placed = True
                                soft_score += 35.0
                            else:
                                soft_score -= 40.0
                        elif not match_slot and polarity == "POSITIVE" and len(c_days) >= 3:
                            soft_score -= 3.0

                    # 3. Room Allocation
                    if c_room and (c_course and c_course.lower() in sess.course_name.lower()):
                        if c_room.lower() in room_name.lower():
                            soft_score += 15.0
                        else:
                            soft_score -= 5.0

                    # 4. Batch Preference
                    if c_batch and (sess.batch and c_batch.lower() in sess.batch.lower()):
                        match_day = (not c_days) or (day_name in c_days)
                        match_period = (
                            (c_period == "morning" and slot in morning_slots) or
                            (c_period == "afternoon" and slot in afternoon_slots)
                        )
                        if match_day and match_period:
                            soft_score += (10.0 if polarity == "POSITIVE" else -20.0)

                    # 5. Free Slot
                    if intent == "FREE_SLOT_CONSTRAINT" or (polarity == "NEGATIVE" and not c_course and not c_faculty):
                        if c_days and day_name in c_days:
                            if c_period == "afternoon" and slot in afternoon_slots:
                                soft_score -= 15.0
                            elif c_slot and slot < len(self.time_slots) and self.time_slots[slot] == c_slot:
                                soft_score -= 25.0

                if intent == "MOVE_SESSION" and polarity == "POSITIVE" and not target_placed:
                    soft_score -= 30.0

        # ── Combined fitness ──────────────────────────────────────────────────
        if hard_penalty == 0:
            return soft_score
        else:
            return -hard_penalty * 200.0 + soft_score * 0.01

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
                if not self.nlp_constraints or gen >= min(75, self.num_generations):
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
        division_slot: Dict[Tuple[int, int], int] = {}
        batch_day_slots: Dict[str, Dict[Tuple[int, int], int]] = {b: {} for b in self.batches}

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

            # Division-level theory slot conflict
            if sess.session_type == "theory":
                ds_key = (day, slot)
                if ds_key in division_slot:
                    violations += 1
                else:
                    division_slot[ds_key] = i

            # Student batch conflict
            assigned_batches = self.batches if sess.session_type == "theory" else ([sess.batch] if sess.batch else self.batches)
            for b in assigned_batches:
                if b not in batch_day_slots:
                    batch_day_slots[b] = {}
                for s in range(slot, slot + sess.duration):
                    b_key = (day, s)
                    if b_key in batch_day_slots[b]:
                        violations += 1
                    else:
                        batch_day_slots[b][b_key] = i

        return violations

    def evaluate_nlp_satisfaction(self, chromosome) -> Dict[str, Any]:
        """
        Evaluates how well the chromosome satisfied each natural language soft constraint.
        Returns a detailed evaluation report and an overall satisfaction rate (0-100%).
        """
        if not self.nlp_constraints or not chromosome:
            return {"satisfaction_rate": 100, "evaluations": []}

        morning_slots = set(range(0, max(1, self.num_slots // 2)))
        afternoon_slots = set(range(max(1, self.num_slots // 2), self.num_slots))
        evaluations = []
        satisfied_count = 0

        for c in self.nlp_constraints:
            raw_text = c.get("raw_text", "")
            intent = c.get("intent", "")
            polarity = c.get("polarity", "POSITIVE")
            c_faculty = c.get("faculty")
            c_course = c.get("course")
            c_room = c.get("room")
            c_batch = c.get("batch")
            c_days = set(c.get("days", []))
            c_period = c.get("period")
            c_slot = c.get("specific_slot")

            matched_sessions = []
            satisfied = True
            reason = "Constraint conditions satisfied."

            for i, (day, slot, room_idx) in enumerate(chromosome):
                sess = self.sessions[i]
                day_name = self.days[day] if day < len(self.days) else ""
                room_name = self._all_rooms_meta[room_idx]["name"] if room_idx < len(self._all_rooms_meta) else ""

                fac_match = (not c_faculty) or (c_faculty.lower() in sess.faculty.lower())
                crs_match = (not c_course) or (c_course.lower() in sess.course_name.lower())
                bch_match = (not c_batch) or (sess.batch and c_batch.lower() in sess.batch.lower())

                if fac_match and crs_match and bch_match:
                    matched_sessions.append((sess, day_name, slot, room_name))

            if matched_sessions:
                is_specific_target = (
                    (intent == "MOVE_SESSION") or
                    ("move" in raw_text.lower()) or
                    ("shift" in raw_text.lower()) or
                    ("change" in raw_text.lower()) or
                    (c_days and len(c_days) < len(matched_sessions))
                )

                if is_specific_target and polarity == "POSITIVE":
                    found_target = False
                    for sess, day_name, slot, room_name in matched_sessions:
                        in_morning = slot in morning_slots
                        in_afternoon = slot in afternoon_slots
                        in_days = (not c_days) or (day_name in c_days)
                        in_slot = (not c_slot) or (slot < len(self.time_slots) and (self.time_slots[slot] == c_slot or c_slot in self.time_slots[slot]))
                        in_period = (not c_period) or (c_period == "morning" and in_morning) or (c_period == "afternoon" and in_afternoon)
                        in_room = (not c_room) or (c_room.lower() in room_name.lower())

                        if in_days and in_slot and in_period and in_room:
                            found_target = True
                            break
                    if found_target:
                        satisfied = True
                        reason = "Successfully scheduled session at target day/slot."
                    else:
                        satisfied = False
                        reason = "Target session could not be placed without creating hard constraint conflict."
                else:
                    for sess, day_name, slot, room_name in matched_sessions:
                        in_morning = slot in morning_slots
                        in_afternoon = slot in afternoon_slots
                        in_days = (not c_days) or (day_name in c_days)
                        in_slot = (not c_slot) or (slot < len(self.time_slots) and (self.time_slots[slot] == c_slot or c_slot in self.time_slots[slot]))

                        if polarity == "POSITIVE":
                            if c_days and not in_days:
                                satisfied = False
                                reason = f"Scheduled on {day_name} instead of requested {', '.join(c_days)}."
                            if c_period == "morning" and not in_morning:
                                satisfied = False
                                reason = f"Scheduled in afternoon ({self.time_slots[slot] if slot < len(self.time_slots) else slot})."
                            elif c_period == "afternoon" and not in_afternoon:
                                satisfied = False
                                reason = f"Scheduled in morning ({self.time_slots[slot] if slot < len(self.time_slots) else slot})."
                            if c_room and c_room.lower() not in room_name.lower():
                                satisfied = False
                                reason = f"Assigned to {room_name} instead of {c_room}."
                        else:  # NEGATIVE (Avoid)
                            if (not c_days or in_days) and ((c_period == "morning" and in_morning) or (c_period == "afternoon" and in_afternoon) or in_slot):
                                satisfied = False
                                reason = f"Found conflicting session scheduled at {day_name} {self.time_slots[slot] if slot < len(self.time_slots) else slot}."
            else:
                # If target entity not found in chromosome
                if intent == "FREE_SLOT_CONSTRAINT":
                    # Check if requested free slot has sessions
                    occupied_count = 0
                    for i, (day, slot, _) in enumerate(chromosome):
                        d_name = self.days[day] if day < len(self.days) else ""
                        if c_days and d_name in c_days:
                            if (c_period == "afternoon" and slot in afternoon_slots) or (c_slot and slot < len(self.time_slots) and self.time_slots[slot] == c_slot):
                                occupied_count += 1
                    if occupied_count > 0:
                        satisfied = False
                        reason = f"Slot has {occupied_count} sessions scheduled."

            if satisfied:
                satisfied_count += 1
                status = "Satisfied"
            else:
                status = "Violated"

            evaluations.append({
                "text": raw_text,
                "intent": intent,
                "polarity": polarity,
                "status": status,
                "details": reason
            })

        rate = round((satisfied_count / max(1, len(self.nlp_constraints))) * 100)
        return {
            "satisfaction_rate": rate,
            "evaluations": evaluations
        }


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

    # ── Parse NLP Constraints (if provided in plain English) ────────────────
    nlp_text = config_dict.get("nlp_constraints_text", "").strip()
    nlp_constraints = config_dict.get("nlp_constraints", [])
    if nlp_text and not nlp_constraints:
        all_crs_names = [tc.name for tc in theory_courses] + [lc.name for lc in lab_courses]
        all_fac_names = [tc.faculty for tc in theory_courses] + [lc.faculty for lc in lab_courses]
        all_rm_names = [tr.name for tr in theory_rooms] + [lr.name for lr in lab_rooms]
        nlp_constraints = nlp_engine.parse_natural_language_constraints(
            nlp_text,
            courses=all_crs_names,
            faculties=all_fac_names,
            rooms=all_rm_names,
            batches=batches,
            days=days_raw,
            time_slots=slots_raw,
        )

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
        nlp_constraints=nlp_constraints,
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
    nlp_eval = ga.evaluate_nlp_satisfaction(best_chromosome)

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
        "nlp_results":       nlp_eval,
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
    division_slot: Dict[Tuple[int, int], int] = {}
    batch_day_slots: Dict[str, Dict[Tuple[int, int], int]] = {b: {} for b in ga.batches}

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

        # Division slot conflict
        if sess.session_type == "theory":
            ds_key = (day, slot)
            if ds_key in division_slot:
                other_sess = ga.sessions[division_slot[ds_key]]
                msgs.append(f"Division slot conflict: '{sess.course_name}' and '{other_sess.course_name}' both scheduled on {day_label} @ {slot_label}.")
            else:
                division_slot[ds_key] = i

        # Student batch conflict
        assigned_batches = ga.batches if sess.session_type == "theory" else ([sess.batch] if sess.batch else ga.batches)
        for b in assigned_batches:
            if b not in batch_day_slots:
                batch_day_slots[b] = {}
            for s in range(slot, slot + sess.duration):
                b_key = (day, s)
                if b_key in batch_day_slots[b]:
                    other_sess = ga.sessions[batch_day_slots[b][b_key]]
                    msgs.append(f"Student conflict: {b} is scheduled for both '{sess.course_name}' and '{other_sess.course_name}' on {day_label} @ {slots_raw[s] if s < len(slots_raw) else s}.")
                else:
                    batch_day_slots[b][b_key] = i

    return msgs[:30]  # cap at 30 messages


def run_ga_edit(csv_text: str, edit_instruction: str, config_dict=None) -> Dict[str, Any]:
    """
    Direct Targeted Timetable Edit Engine:
    1. Parses uploaded timetable CSV without corrupting or duplicating sessions.
    2. Understands the admin's change instruction in plain English.
    3. Validates the requested change against hard constraints:
       - If the edit causes a conflict: preserves the schedule 100% unchanged,
         notifies the admin of the exact conflict, and provides actionable suggestions.
       - If valid: moves ONLY the requested session while keeping all other sessions intact.
    """
    import re
    if config_dict is None:
        config_dict = {}

    parsed_csv = nlp_engine.parse_timetable_csv(csv_text)
    days_raw = parsed_csv["days"]
    slots_raw = parsed_csv["time_slots"]
    uploaded_schedule = parsed_csv["schedule"]

    if not uploaded_schedule:
        raise ValueError("No valid schedule sessions found in uploaded CSV.")

    # Reconstruct room lists
    theory_rooms_set = set()
    lab_rooms_set = set()
    for s in uploaded_schedule:
        if s["type"] == "lab":
            lab_rooms_set.add(s["room"])
        else:
            theory_rooms_set.add(s["room"])
    if not theory_rooms_set:
        theory_rooms_set.add("Classroom 101")

    theory_rooms_list = sorted(list(theory_rooms_set))
    lab_rooms_list = sorted(list(lab_rooms_set))
    all_rooms_list = theory_rooms_list + lab_rooms_list
    all_batches_list = parsed_csv["batches"] or ["Batch A", "Batch B", "Batch C"]
    all_crs = sorted(list(set(s["course"] for s in uploaded_schedule)))
    all_fac = sorted(list(set(s["faculty"] for s in uploaded_schedule if s["faculty"])))

    # Parse NLP edit instruction
    nlp_constraints = nlp_engine.parse_natural_language_constraints(
        edit_instruction,
        courses=all_crs,
        faculties=all_fac,
        rooms=all_rooms_list,
        batches=all_batches_list,
        days=days_raw,
        time_slots=slots_raw
    )

    # Slot & Day helper matchers
    def match_slot(text_or_alias: str) -> Optional[str]:
        if not text_or_alias:
            return None
        t = text_or_alias.strip().lower()
        # 1. Substring match for full slot string
        for s in slots_raw:
            if s.lower() in t or s.replace("–", "-").lower() in t:
                return s
        # 2. Match HH:MM - HH:MM
        m_full = re.search(r'\b(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})\b', t)
        if m_full:
            h1 = int(m_full.group(1))
            h2 = int(m_full.group(3))
            cand = f"{h1:02d}:00 - {h2:02d}:00"
            for s in slots_raw:
                if cand == s or cand.replace(" - ", "-") in s:
                    return s
        # 3. Match N-N (without colons, e.g. 8-9, 3-4, 12-1)
        m = re.search(r'(?<!:)\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b(?!:)', t)
        if m:
            h1 = int(m.group(1))
            h2 = int(m.group(2))
            start_h = h1 if h1 >= 7 else h1 + 12
            end_h = h2 if h2 >= 7 else h2 + 12
            cand = f"{start_h:02d}:00 - {end_h:02d}:00"
            for s in slots_raw:
                if cand == s or f"{h1}-{h2}" == s:
                    return s
            return cand
        # 4. Match N am / N pm
        m_hour = re.search(r'\b(\d{1,2})\s*(am|pm)\b', t)
        if m_hour:
            h = int(m_hour.group(1))
            is_pm = m_hour.group(2) == 'pm'
            start_h = h if not is_pm else (h if h == 12 else h + 12)
            end_h = start_h + 1
            cand = f"{start_h:02d}:00 - {end_h:02d}:00"
            for s in slots_raw:
                if cand == s:
                    return s
        return None

    def match_day(text_or_alias: str) -> Optional[str]:
        if not text_or_alias:
            return None
        lower = text_or_alias.strip().lower()
        days_map = {
            "monday": "Monday", "mon": "Mon",
            "tuesday": "Tuesday", "tue": "Tue",
            "wednesday": "Wednesday", "wed": "Wed",
            "thursday": "Thursday", "thu": "Thu",
            "friday": "Friday", "fri": "Fri",
            "saturday": "Saturday", "sat": "Sat",
            "sunday": "Sunday", "sun": "Sun",
        }
        for alias, std in days_map.items():
            if re.search(r'\b' + alias + r'\b', lower):
                for kd in days_raw:
                    if kd.lower() == alias or kd.lower() == std.lower() or kd.lower() == alias[:3]:
                        return kd
                return std
        return None

    # Check for "from <src> to <dst>"
    m_from_to = re.search(r'from\s+(.+?)\s+to\s+(.+)$', edit_instruction.lower())
    src_text = m_from_to.group(1) if m_from_to else ""
    dst_text = m_from_to.group(2) if m_from_to else edit_instruction.lower()

    c_info = nlp_constraints[0] if nlp_constraints else {}
    target_course = c_info.get("course")
    target_faculty = c_info.get("faculty")
    target_batch = c_info.get("batch")

    if not target_course:
        for c in all_crs:
            if c.lower() in edit_instruction.lower():
                target_course = c
                break

    source_day = match_day(src_text)
    source_slot = match_slot(src_text)

    dest_day = match_day(dst_text) or (c_info.get("days", [None])[0] if c_info.get("days") else None)
    dest_slot = match_slot(dst_text) or match_slot(c_info.get("specific_slot", ""))
    dest_period = c_info.get("period")
    if not dest_period:
        if "morning" in dst_text: dest_period = "morning"
        elif "afternoon" in dst_text: dest_period = "afternoon"
    dest_room = c_info.get("room")

    # Locate the target session in uploaded_schedule
    target_idx = None
    # 1. By course and source day/slot
    if target_course:
        for idx, s in enumerate(uploaded_schedule):
            if target_course.lower() in s["course"].lower():
                if source_day and s["day"].lower() != source_day.lower():
                    continue
                if source_slot and s["slot"] != source_slot:
                    continue
                target_idx = idx
                break

    # 2. By course (first session not already at destination)
    if target_idx is None and target_course:
        for idx, s in enumerate(uploaded_schedule):
            if target_course.lower() in s["course"].lower():
                if dest_day and s["day"].lower() == dest_day.lower() and dest_slot and s["slot"] == dest_slot:
                    continue
                target_idx = idx
                break

    # 3. By faculty
    if target_idx is None and target_faculty:
        for idx, s in enumerate(uploaded_schedule):
            if target_faculty.lower() in s["faculty"].lower():
                target_idx = idx
                break

    # Helper: validate move of session to (cand_d, cand_s, cand_r) against other sessions
    def validate_move(sess_item, cand_d, cand_s, cand_r, other_sessions):
        conflicts = []
        is_theory = (sess_item["type"] == "theory")
        duration = sess_item.get("duration", 2 if not is_theory else 1)
        sess_batches = all_batches_list if is_theory else ([sess_item["batch"]] if sess_item.get("batch") else all_batches_list)

        s_idx = slots_raw.index(cand_s) if cand_s in slots_raw else -1
        if s_idx < 0:
            return ["Invalid time slot specified."]
        if s_idx + duration > len(slots_raw):
            return ["Session duration exceeds daily time boundary."]

        cand_slots = slots_raw[s_idx:s_idx + duration]

        # Check course repeat limit (max 1 session per course per day)
        if cand_d != sess_item["day"]:
            for o in other_sessions:
                if o["course"].lower() == sess_item["course"].lower() and o["day"] == cand_d:
                    conflicts.append(f"Course repeat limit: '{sess_item['course']}' is already scheduled on {cand_d}. A course cannot appear more than once per day.")
                    break

        for o in other_sessions:
            o_dur = o.get("duration", 2 if o["type"] == "lab" else 1)
            o_sidx = slots_raw.index(o["slot"]) if o["slot"] in slots_raw else -1
            if o_sidx < 0 or o["day"] != cand_d:
                continue
            o_slots = slots_raw[o_sidx:o_sidx + o_dur]

            # Overlapping slots between cand_slots and o_slots
            overlap = any(sl in o_slots for sl in cand_slots)
            if not overlap:
                continue

            # 1. Division conflict (Theory vs Theory)
            if is_theory and o["type"] == "theory":
                conflicts.append(f"Division slot conflict: Theory lecture '{o['course']}' is already scheduled on {cand_d} @ {o['slot']}.")

            # 2. Student batch conflict
            o_batches = all_batches_list if o["type"] == "theory" else ([o["batch"]] if o.get("batch") else all_batches_list)
            for b in sess_batches:
                if b in o_batches:
                    conflicts.append(f"Student conflict: {b} is already attending '{o['course']}' on {cand_d} @ {o['slot']}.")
                    break

            # 3. Faculty conflict
            if sess_item.get("faculty") and o.get("faculty") and sess_item["faculty"].lower() == o["faculty"].lower():
                conflicts.append(f"Faculty conflict: {sess_item['faculty']} is already teaching '{o['course']}' on {cand_d} @ {o['slot']}.")

            # 4. Room conflict
            if cand_r and o.get("room") and cand_r.lower() == o["room"].lower():
                conflicts.append(f"Room conflict: Room '{cand_r}' is already occupied by '{o['course']}' on {cand_d} @ {o['slot']}.")

        return conflicts

    # If target session found
    schedule = copy.deepcopy(uploaded_schedule)
    conflict_detected = False
    conflict_messages = []
    suggestions = []

    if target_idx is not None:
        target_sess = schedule[target_idx]
        other_sess_list = [s for idx, s in enumerate(schedule) if idx != target_idx]

        final_day = dest_day or target_sess["day"]
        final_slot = dest_slot

        # If slot was not explicitly specified, find first candidate in period
        if not final_slot and dest_period:
            mid = len(slots_raw) // 2
            cand_range = slots_raw[:mid] if dest_period == "morning" else slots_raw[mid:]
            for cs in cand_range:
                test_r = dest_room or target_sess["room"]
                test_errs = validate_move(target_sess, final_day, cs, test_r, other_sess_list)
                if not test_errs:
                    final_slot = cs
                    break

        if not final_slot:
            final_slot = target_sess["slot"]

        # Choose room
        final_room = dest_room
        if not final_room:
            # Pick a free room of correct type
            allowed_rooms = theory_rooms_list if target_sess["type"] == "theory" else lab_rooms_list
            occupied_rooms = set(
                o["room"] for o in other_sess_list
                if o["day"] == final_day and o["slot"] == final_slot
            )
            free_rooms = [r for r in allowed_rooms if r not in occupied_rooms]
            final_room = free_rooms[0] if free_rooms else target_sess["room"]

        # Validate the proposed edit
        conflict_messages = validate_move(target_sess, final_day, final_slot, final_room, other_sess_list)

        if conflict_messages:
            conflict_detected = True
            # Find suggestions where this session CAN be placed with 0 conflicts
            for d in days_raw:
                for sl in slots_raw:
                    if d == target_sess["day"] and sl == target_sess["slot"]:
                        continue
                    test_cands = validate_move(target_sess, d, sl, final_room, other_sess_list)
                    if not test_cands:
                        suggestions.append(f"{d} {sl}")
                        if len(suggestions) >= 4:
                            break
                if len(suggestions) >= 4:
                    break
        else:
            # Apply targeted change: ONLY the target session moves!
            target_sess["day"] = final_day
            target_sess["slot"] = final_slot
            target_sess["time_label"] = final_slot
            target_sess["room"] = final_room
            schedule[target_idx] = target_sess
    else:
        conflict_detected = True
        conflict_messages = [f"Could not identify a session matching '{edit_instruction}' in the uploaded timetable."]

    # Rebuild grids cleanly from schedule
    grid_by_day = {d: {s: [] for s in slots_raw} for d in days_raw}
    for entry in schedule:
        d = entry["day"]
        s = entry["slot"]
        if d in grid_by_day and s in grid_by_day[d]:
            grid_by_day[d][s].append(entry)

    grid_by_room = {rm: {d: {s: [] for s in slots_raw} for d in days_raw} for rm in all_rooms_list}
    for entry in schedule:
        rm = entry["room"]
        d = entry["day"]
        s = entry["slot"]
        if rm in grid_by_room and d in grid_by_room[rm] and s in grid_by_room[rm][d]:
            grid_by_room[rm][d][s].append(entry)

    all_entities = sorted(list(set(s.get("batch") or "Whole Division" for s in schedule) | set(["Whole Division"])))
    grid_by_batch = {ent: {d: {s: [] for s in slots_raw} for d in days_raw} for ent in all_entities}
    for entry in schedule:
        d = entry["day"]
        s = entry["slot"]
        ent = entry.get("batch") or "Whole Division"
        targets = all_entities if ent == "Whole Division" else [ent]
        for t_ent in targets:
            if t_ent in grid_by_batch and d in grid_by_batch[t_ent] and s in grid_by_batch[t_ent][d]:
                grid_by_batch[t_ent][d][s].append(entry)

    # Format NLP evaluations
    eval_item = {
        "text": edit_instruction,
        "status": "Conflict Detected" if conflict_detected else "Satisfied",
        "polarity": "NEGATIVE" if conflict_detected else "POSITIVE",
        "details": (
            f"Cannot apply requested change: {'; '.join(conflict_messages)}. The existing timetable was preserved to prevent schedule corruption."
            if conflict_detected else
            f"Successfully updated '{schedule[target_idx]['course']}' to {schedule[target_idx]['day']} @ {schedule[target_idx]['slot']} in {schedule[target_idx]['room']}. All other sessions preserved."
        ),
        "suggestions": suggestions
    }

    return {
        "schedule":          schedule,
        "grid_by_day":       grid_by_day,
        "grid_by_room":      grid_by_room,
        "grid_by_batch":     grid_by_batch,
        "all_rooms":         all_rooms_list,
        "theory_rooms":      theory_rooms_list,
        "lab_rooms":         lab_rooms_list,
        "all_batches":       all_entities,
        "days":              days_raw,
        "time_slots":        slots_raw,
        "fitness":           100.0 if not conflict_detected else 0.0,
        "violations":        len(conflict_messages) if conflict_detected else 0,
        "violation_detail":  conflict_messages if conflict_detected else [],
        "conflict_detected": conflict_detected,
        "fitness_history":   [100.0],
        "generations_run":   1,
        "total_sessions":    len(schedule),
        "theory_sessions":   sum(1 for s in schedule if s["type"] == "theory"),
        "lab_sessions":      sum(1 for s in schedule if s["type"] == "lab"),
        "nlp_results": {
            "mode": "edit",
            "instruction": edit_instruction,
            "parsed_constraints": nlp_constraints,
            "satisfaction_rate": 0 if conflict_detected else 100,
            "status": "Conflict Detected - Schedule Preserved" if conflict_detected else "Satisfied",
            "evaluations": [eval_item]
        },
        "config": {
            "population_size":   100,
            "mutation_rate":     0.05,
            "crossover_rate":    0.8,
            "max_generations":   100,
            "elitism_count":     2,
            "tournament_k":      3,
            "num_theory_rooms":  len(theory_rooms_list),
            "num_lab_rooms":     len(lab_rooms_list),
            "num_days":          len(days_raw),
            "num_slots":         len(slots_raw),
            "prefer_theory_time": "unbiased",
            "prefer_lab_time":    "unbiased",
            "lunch_window":      [],
        },
    }


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
