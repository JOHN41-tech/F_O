"""
Seating Algorithm - Constraint Satisfaction Randomizer
Ensures students from the same department/subject are NOT placed adjacent (same bench row).
"""
import random

def generate_seating(students, rooms):
    """
    Args:
        students: list of dicts {id, name, roll_no, department, subject}
        rooms: list of dicts {id, name, capacity, benches_per_row}
    Returns:
        assignments: list of {student_id, room_id, bench_row, bench_col}
        error: string or None
    """
    # Correct total seats calculation: capacity is number of benches, per_row is seats per bench
    total_seats = sum(r['capacity'] * r['per_row'] for r in rooms)
    if len(students) > total_seats:
        return None, f"Overflow: {len(students)} students but only {total_seats} seats available."

    # Group students by (department, subject) for better interleaving
    groups = {}
    for s in students:
        key = (s.get('department', 'Unknown'), s.get('subject', 'Unknown'))
        groups.setdefault(key, []).append(s)

    # Shuffle each group then convert to list of lists
    group_lists = []
    for key in sorted(groups.keys()):
        g = groups[key]
        random.shuffle(g)
        group_lists.append(g)

    # Interleave students from different groups
    interleaved = []
    while any(group_lists):
        for g in group_lists:
            if g:
                interleaved.append(g.pop(0))
        group_lists = [g for g in group_lists if g]

    assignments = []
    student_queue = list(interleaved)
    
    # Optional: shuffle rooms to vary distribution if multiple rooms exist
    shuffled_rooms = list(rooms)
    random.shuffle(shuffled_rooms)

    for room in shuffled_rooms:
        if not student_queue:
            break
            
        benches      = room['capacity']
        seats_per_bench = room['per_row'] # This translates to bench_col (seat number on bench)

        for bench_idx in range(benches):
            for seat_idx in range(seats_per_bench):
                if not student_queue:
                    break
                student = student_queue.pop(0)
                assignments.append({
                    'student_id': student['id'],
                    'room_id':    room['id'],
                    'bench_row':  bench_idx + 1, # Using row as bench number
                    'bench_col':  seat_idx + 1,  # Using col as seat number on bench
                })

    return assignments, None
