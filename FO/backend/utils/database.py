import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.getenv('DATABASE_PATH', 'learning_assistant.db')

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Topics table
    c.execute('''CREATE TABLE IF NOT EXISTS topics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  total_steps INTEGER,
                  current_step INTEGER DEFAULT 0,
                  completed BOOLEAN DEFAULT 0,
                  roadmap_data TEXT)''')
    
    # Progress table
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_id INTEGER,
                  step_number INTEGER,
                  completed BOOLEAN DEFAULT 0,
                  time_spent INTEGER DEFAULT 0,
                  completed_at TIMESTAMP,
                  FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    
    # Notes table
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_id INTEGER,
                  step_number INTEGER,
                  content TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    
    # Chat history table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_id INTEGER,
                  step_number INTEGER,
                  role TEXT,
                  message TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    
    # Quiz results table
    c.execute('''CREATE TABLE IF NOT EXISTS quiz_results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_id INTEGER,
                  step_number INTEGER,
                  score INTEGER,
                  total_questions INTEGER,
                  completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (topic_id) REFERENCES topics(id))''')

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  role TEXT NOT NULL DEFAULT 'student',
                  password_hash TEXT)''')
    
    # Events table (Club Proposals)
    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  category TEXT,
                  status TEXT DEFAULT 'Pending',
                  coordinator_id INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (coordinator_id) REFERENCES users(id))''')
    
    # Schedules table (Academic Calendar)
    c.execute('''CREATE TABLE IF NOT EXISTS schedules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_type TEXT NOT NULL,
                  start_date DATE NOT NULL,
                  end_date DATE,
                  description TEXT,
                  is_exam BOOLEAN DEFAULT 0)''')
    
    # Hall tickets release status
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY,
                  value TEXT)''')
    
    # Insert default settings if not exists
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('hall_tickets_released', '0')")

    # Migration: add source_proposal_id to schedules if it doesn't exist
    try:
        c.execute("ALTER TABLE schedules ADD COLUMN source_proposal_id INTEGER DEFAULT NULL")
    except Exception:
        pass  # Column already exists

    # Insert default admin if not exists (for testing)
    c.execute("INSERT OR IGNORE INTO users (username, role) VALUES ('admin', 'admin')")

    # Clubs table
    c.execute('''CREATE TABLE IF NOT EXISTS clubs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  bio TEXT,
                  logo_path TEXT,
                  instagram TEXT,
                  linkedin TEXT,
                  coordinator_id INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (coordinator_id) REFERENCES users(id))''')

    # Club members table
    c.execute('''CREATE TABLE IF NOT EXISTS club_members
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  club_id INTEGER,
                  name TEXT NOT NULL,
                  email TEXT,
                  FOREIGN KEY (club_id) REFERENCES clubs(id))''')

    # Event proposals table
    c.execute('''CREATE TABLE IF NOT EXISTS event_proposals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  club_id INTEGER,
                  title TEXT NOT NULL,
                  description TEXT,
                  event_date DATE,
                  venue TEXT,
                  expected_attendance INTEGER,
                  budget_note TEXT,
                  file_path TEXT,
                  status TEXT DEFAULT 'Draft',
                  admin_comment TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (club_id) REFERENCES clubs(id))''')

    # ─── Seating Manager Tables ─────────────────────────────────────────────

    # Rooms table
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  capacity INTEGER NOT NULL,
                  benches_per_row INTEGER DEFAULT 4)''')

    # Exams table
    c.execute('''CREATE TABLE IF NOT EXISTS exams
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  exam_date DATE,
                  status TEXT DEFAULT 'draft')''')

    # Students for exam table
    c.execute('''CREATE TABLE IF NOT EXISTS exam_students
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  exam_id INTEGER,
                  name TEXT NOT NULL,
                  roll_no TEXT NOT NULL,
                  department TEXT,
                  subject TEXT,
                  FOREIGN KEY (exam_id) REFERENCES exams(id))''')

    # Seating assignments table
    c.execute('''CREATE TABLE IF NOT EXISTS seating_assignments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  exam_id INTEGER,
                  student_id INTEGER,
                  room_id INTEGER,
                  bench_row INTEGER,
                  bench_col INTEGER,
                  FOREIGN KEY (exam_id) REFERENCES exams(id),
                  FOREIGN KEY (student_id) REFERENCES exam_students(id),
                  FOREIGN KEY (room_id) REFERENCES rooms(id))''')
    
    conn.commit()
    conn.close()

def save_topic(name, roadmap_data, total_steps):
    """Save a new topic to the database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO topics (name, total_steps, roadmap_data)
                 VALUES (?, ?, ?)''', (name, total_steps, json.dumps(roadmap_data)))
    
    topic_id = c.lastrowid
    
    # Initialize progress for all steps
    for i in range(total_steps):
        c.execute('''INSERT INTO progress (topic_id, step_number)
                     VALUES (?, ?)''', (topic_id, i))
    
    conn.commit()
    conn.close()
    return topic_id

def get_all_topics():
    """Get all topics"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, name, total_steps, current_step, completed, last_accessed
                 FROM topics ORDER BY last_accessed DESC''')
    
    topics = []
    for row in c.fetchall():
        topics.append({
            'id': row[0],
            'name': row[1],
            'total_steps': row[2],
            'current_step': row[3],
            'completed': bool(row[4]),
            'last_accessed': row[5]
        })
    
    conn.close()
    return topics

def get_topic(topic_id):
    """Get a specific topic"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, name, total_steps, current_step, roadmap_data
                 FROM topics WHERE id = ?''', (topic_id,))
    
    row = c.fetchone()
    if row:
        topic = {
            'id': row[0],
            'name': row[1],
            'total_steps': row[2],
            'current_step': row[3],
            'roadmap_data': json.loads(row[4])
        }
    else:
        topic = None
    
    conn.close()
    return topic

def update_topic_progress(topic_id, step_number):
    """Update the current step for a topic"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''UPDATE topics SET current_step = ?, last_accessed = CURRENT_TIMESTAMP
                 WHERE id = ?''', (step_number, topic_id))
    
    conn.commit()
    conn.close()

def save_note(topic_id, step_number, content):
    """Save or update a note"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if note exists
    c.execute('''SELECT id FROM notes WHERE topic_id = ? AND step_number = ?''',
              (topic_id, step_number))
    
    if c.fetchone():
        c.execute('''UPDATE notes SET content = ?, updated_at = CURRENT_TIMESTAMP
                     WHERE topic_id = ? AND step_number = ?''',
                  (content, topic_id, step_number))
    else:
        c.execute('''INSERT INTO notes (topic_id, step_number, content)
                     VALUES (?, ?, ?)''', (topic_id, step_number, content))
    
    conn.commit()
    conn.close()

def get_note(topic_id, step_number):
    """Get a note for a specific step"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT content FROM notes WHERE topic_id = ? AND step_number = ?''',
              (topic_id, step_number))
    
    row = c.fetchone()
    note = row[0] if row else None
    
    conn.close()
    return note

def save_chat_message(topic_id, step_number, role, message):
    """Save a chat message"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO chat_history (topic_id, step_number, role, message)
                 VALUES (?, ?, ?, ?)''', (topic_id, step_number, role, message))
    
    conn.commit()
    conn.close()

def get_chat_history(topic_id, step_number, limit=10):
    """Get chat history for a step"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT role, message, created_at FROM chat_history
                 WHERE topic_id = ? AND step_number = ?
                 ORDER BY created_at DESC LIMIT ?''',
              (topic_id, step_number, limit))
    
    messages = []
    for row in c.fetchall():
        messages.append({
            'role': row[0],
            'message': row[1],
            'created_at': row[2]
        })
    
    conn.close()
    return list(reversed(messages))

def clear_chat_history(topic_id, step_number):
    """Clear chat history for a specific step"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''DELETE FROM chat_history 
                 WHERE topic_id = ? AND step_number = ?''',
              (topic_id, step_number))
    
    conn.commit()
    conn.close()

def save_quiz_result(topic_id, step_number, score, total_questions):
    """Save quiz results"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO quiz_results (topic_id, step_number, score, total_questions)
                 VALUES (?, ?, ?, ?)''', (topic_id, step_number, score, total_questions))
    
    conn.commit()
    conn.close()

def get_quiz_results(topic_id):
    """Get all quiz results for a topic"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT step_number, score, total_questions, completed_at
                 FROM quiz_results WHERE topic_id = ?
                 ORDER BY step_number''', (topic_id,))
    
    results = []
    for row in c.fetchall():
        results.append({
            'step_number': row[0],
            'score': row[1],
            'total_questions': row[2],
            'completed_at': row[3]
        })
    
    conn.close()
    return results

# Admin Helper Functions

def get_all_schedules():
    """Get all academic calendar events"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, event_type, start_date, end_date, description, is_exam FROM schedules ORDER BY start_date")
    schedules = []
    for row in c.fetchall():
        schedules.append({
            'id': row[0],
            'type': row[1],
            'start': row[2],
            'end': row[3],
            'details': row[4],
            'is_exam': bool(row[5])
        })
    conn.close()
    return schedules

def add_schedule(event_type, start_date, end_date, description, is_exam=False):
    """Add a new event to the academic calendar"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO schedules (event_type, start_date, end_date, description, is_exam) VALUES (?, ?, ?, ?, ?)",
              (event_type, start_date, end_date, description, is_exam))
    conn.commit()
    conn.close()

def get_pending_events():
    """Get all pending club proposals"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT e.id, e.title, e.description, e.category, u.username FROM events e JOIN users u ON e.coordinator_id = u.id WHERE e.status = 'Pending'")
    events = []
    for row in c.fetchall():
        events.append({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'category': row[3],
            'coordinator': row[4]
        })
    conn.close()
    return events

def update_event_status(event_id, status, admin_comment=None):
    """Approve or reject an event proposal (targets event_proposals table)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if admin_comment is not None:
        c.execute("UPDATE event_proposals SET status = ?, admin_comment = ? WHERE id = ?",
                  (status, admin_comment, event_id))
    else:
        c.execute("UPDATE event_proposals SET status = ? WHERE id = ?", (status, event_id))
    conn.commit()
    conn.close()
    # Keep campus calendar in sync
    sync_event_to_calendar(event_id, status)


def sync_event_to_calendar(proposal_id, status):
    """When a proposal is Approved, add/update it in the shared schedules table.
       When Rejected (or re-rejected), remove it from the calendar."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if status == 'Approved':
        # Fetch proposal details
        c.execute('''SELECT title, description, event_date, venue
                     FROM event_proposals WHERE id = ?''', (proposal_id,))
        row = c.fetchone()
        if row:
            title, description, event_date, venue = row
            detail_text = title
            if venue:
                detail_text += f' @ {venue}'
            # Upsert: update if already in calendar, insert if new
            c.execute("SELECT id FROM schedules WHERE source_proposal_id = ?", (proposal_id,))
            existing = c.fetchone()
            if existing:
                c.execute('''UPDATE schedules
                             SET event_type=?, start_date=?, end_date=?, description=?, is_exam=0
                             WHERE source_proposal_id=?''',
                          ('Club Event', event_date, event_date, detail_text, proposal_id))
            else:
                c.execute('''INSERT INTO schedules
                             (event_type, start_date, end_date, description, is_exam, source_proposal_id)
                             VALUES (?, ?, ?, ?, 0, ?)''',
                          ('Club Event', event_date, event_date, detail_text, proposal_id))
    else:
        # Rejected or any non-approved status — remove from calendar
        c.execute("DELETE FROM schedules WHERE source_proposal_id = ?", (proposal_id,))

    conn.commit()
    conn.close()


def get_setting(key):
    """Get a system setting"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def update_setting(key, value):
    """Update a system setting"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# ─── Club Coordinator Helper Functions ───────────────────────────────────────

def save_club_profile(name, bio, logo_path, instagram, linkedin, coordinator_id):
    """Create or update a club profile for a coordinator"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM clubs WHERE coordinator_id = ?", (coordinator_id,))
    row = c.fetchone()
    if row:
        c.execute('''UPDATE clubs SET name=?, bio=?, logo_path=?, instagram=?, linkedin=?
                     WHERE coordinator_id=?''',
                  (name, bio, logo_path, instagram, linkedin, coordinator_id))
        club_id = row[0]
    else:
        c.execute('''INSERT INTO clubs (name, bio, logo_path, instagram, linkedin, coordinator_id)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (name, bio, logo_path, instagram, linkedin, coordinator_id))
        club_id = c.lastrowid
    conn.commit()
    conn.close()
    return club_id

def get_club_by_coordinator(coordinator_id):
    """Get a club's details by coordinator_id"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, bio, logo_path, instagram, linkedin FROM clubs WHERE coordinator_id = ?",
              (coordinator_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'bio': row[2],
                'logo_path': row[3], 'instagram': row[4], 'linkedin': row[5]}
    return None

def save_club_members(club_id, members):
    """Replace members list for a club"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM club_members WHERE club_id = ?", (club_id,))
    for m in members:
        c.execute("INSERT INTO club_members (club_id, name, email) VALUES (?, ?, ?)",
                  (club_id, m.get('name'), m.get('email')))
    conn.commit()
    conn.close()

def get_club_members(club_id):
    """Get all members of a club"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, email FROM club_members WHERE club_id = ?", (club_id,))
    members = [{'name': r[0], 'email': r[1]} for r in c.fetchall()]
    conn.close()
    return members

def submit_proposal(club_id, title, description, event_date, venue, attendance, budget_note, file_path, status='Pending'):
    """Submit or save a new event proposal"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO event_proposals
                 (club_id, title, description, event_date, venue, expected_attendance, budget_note, file_path, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (club_id, title, description, event_date, venue, attendance, budget_note, file_path, status))
    conn.commit()
    conn.close()

def get_proposals_by_club(club_id):
    """Get all proposals submitted by a club"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, title, event_date, venue, status, admin_comment, created_at
                 FROM event_proposals WHERE club_id = ? ORDER BY created_at DESC''', (club_id,))
    proposals = []
    for r in c.fetchall():
        proposals.append({
            'id': r[0], 'title': r[1], 'date': r[2], 'venue': r[3],
            'status': r[4], 'comment': r[5], 'created_at': r[6]
        })
    conn.close()
    return proposals

def check_date_conflict(event_date):
    """Check if a proposed date conflicts with exam blackout dates"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT event_type, start_date, end_date, description FROM schedules
                 WHERE is_exam = 1 AND start_date <= ? AND (end_date >= ? OR end_date IS NULL)''',
              (event_date, event_date))
    conflict = c.fetchone()
    conn.close()
    if conflict:
        return {'conflict': True, 'type': conflict[0], 'start': conflict[1],
                'end': conflict[2], 'desc': conflict[3]}
    return {'conflict': False}

def get_all_proposals_for_admin():
    """Get all non-draft proposals for admin with club names"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT ep.id, ep.title, ep.description, ep.event_date, ep.venue,
                        ep.expected_attendance, ep.budget_note,
                        ep.status, ep.file_path, c.name AS club_name, ep.admin_comment,
                        ep.created_at
                 FROM event_proposals ep
                 LEFT JOIN clubs c ON ep.club_id = c.id
                 WHERE ep.status != 'Draft'
                 ORDER BY ep.created_at DESC''')
    proposals = []
    for r in c.fetchall():
        proposals.append({
            'id': r[0], 'title': r[1], 'description': r[2], 'date': r[3],
            'venue': r[4], 'attendance': r[5], 'budget_note': r[6],
            'status': r[7], 'file': r[8], 'club': r[9], 'comment': r[10],
            'created_at': r[11]
        })
    conn.close()
    return proposals

def update_proposal_comment(proposal_id, comment):
    """Admin adds a comment to a proposal"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE event_proposals SET admin_comment = ? WHERE id = ?", (comment, proposal_id))
    conn.commit()
    conn.close()

# ─── Seating Manager Helper Functions ────────────────────────────────────────

def get_all_rooms():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, capacity, benches_per_row FROM rooms ORDER BY name")
    rooms = [{'id': r[0], 'name': r[1], 'capacity': r[2], 'per_row': r[3]} for r in c.fetchall()]
    conn.close()
    return rooms

def add_room(name, capacity, benches_per_row):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO rooms (name, capacity, benches_per_row) VALUES (?, ?, ?)",
              (name, capacity, benches_per_row))
    room_id = c.lastrowid
    conn.commit()
    conn.close()
    return room_id

def delete_room(room_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    conn.commit()
    conn.close()

def get_all_exams():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, exam_date, status FROM exams ORDER BY exam_date DESC")
    exams = [{'id': r[0], 'name': r[1], 'date': r[2], 'status': r[3]} for r in c.fetchall()]
    conn.close()
    return exams

def create_exam(name, exam_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO exams (name, exam_date) VALUES (?, ?)", (name, exam_date))
    eid = c.lastrowid
    conn.commit()
    conn.close()
    return eid

def add_exam_student(exam_id, name, roll_no, department, subject):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO exam_students (exam_id, name, roll_no, department, subject) VALUES (?, ?, ?, ?, ?)",
              (exam_id, name, roll_no, department, subject))
    conn.commit()
    conn.close()

def get_exam_students(exam_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, roll_no, department, subject FROM exam_students WHERE exam_id = ?", (exam_id,))
    students = [{'id': r[0], 'name': r[1], 'roll_no': r[2], 'department': r[3], 'subject': r[4]}
                for r in c.fetchall()]
    conn.close()
    return students

def save_seating_assignments(exam_id, assignments):
    """Clear old and save new assignments"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM seating_assignments WHERE exam_id = ?", (exam_id,))
    for a in assignments:
        c.execute("INSERT INTO seating_assignments (exam_id, student_id, room_id, bench_row, bench_col) VALUES (?, ?, ?, ?, ?)",
                  (exam_id, a['student_id'], a['room_id'], a['bench_row'], a['bench_col']))
    conn.commit()
    conn.close()

def get_seating_chart(exam_id):
    """Return chart grouped by room"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT sa.bench_row, sa.bench_col, es.name, es.roll_no, es.department,
                        r.name AS room_name, r.id AS room_id, r.benches_per_row
                 FROM seating_assignments sa
                 JOIN exam_students es ON sa.student_id = es.id
                 JOIN rooms r ON sa.room_id = r.id
                 WHERE sa.exam_id = ?
                 ORDER BY r.id, sa.bench_row, sa.bench_col''', (exam_id,))
    rows = c.fetchall()
    conn.close()
    rooms = {}
    for r in rows:
        rid = r[6]
        if rid not in rooms:
            rooms[rid] = {'room_name': r[5], 'room_id': rid, 'per_row': r[7], 'benches': []}
        rooms[rid]['benches'].append({
            'row': r[0], 'col': r[1], 'name': r[2], 'roll': r[3], 'dept': r[4]
        })
    return list(rooms.values())

def search_student_seat(exam_id, roll_no):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT es.name, es.roll_no, es.department, r.name, sa.bench_row, sa.bench_col
                 FROM exam_students es
                 LEFT JOIN seating_assignments sa ON es.id = sa.student_id
                 LEFT JOIN rooms r ON sa.room_id = r.id
                 WHERE es.exam_id = ? AND es.roll_no LIKE ?''', (exam_id, f'%{roll_no}%'))
    row = c.fetchone()
    conn.close()
    if row:
        return {'name': row[0], 'roll': row[1], 'dept': row[2],
                'room': row[3], 'row': row[4], 'col': row[5]}
    return None

def get_student_ticket_info(roll_no):
    """Fetch full hall ticket details for a student if the exam is finalized"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT es.name, es.roll_no, es.department, es.subject, 
                        e.name AS exam_name, e.exam_date,
                        r.name AS room_name, sa.bench_row, sa.bench_col
                 FROM exam_students es
                 JOIN exams e ON es.exam_id = e.id
                 JOIN seating_assignments sa ON es.id = sa.student_id
                 JOIN rooms r ON sa.room_id = r.id
                 WHERE es.roll_no = ? AND e.status = 'seating_ready'
                 ORDER BY e.exam_date DESC LIMIT 1''', (roll_no,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'name': row[0], 'roll_no': row[1], 'department': row[2], 'subject': row[3],
            'exam_name': row[4], 'exam_date': row[5],
            'room': row[6], 'row': row[7], 'col': row[8]
        }
    return None

def finalize_exam(exam_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE exams SET status = 'seating_ready' WHERE id = ?", (exam_id,))
    # Also update global setting to notify Admin
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('seating_ready', '1')")
    conn.commit()
    conn.close()

# Initialize database on import
init_db()
