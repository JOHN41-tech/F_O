from flask import Flask, render_template, request, jsonify, session, make_response
import os
from dotenv import load_dotenv
from backend.core.session import LearningSession
from backend.api.perplexity import PerplexityClient
import backend.utils.database as db
from backend.utils.quiz_generator import QuizGenerator
import json
import pandas as pd
import io

from functools import wraps

load_dotenv()

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For demo purposes, we'll check a cookie. In production, use session/JWT
        role = request.cookies.get('user_role', 'student')
        if role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Store sessions in memory
sessions = {}
quiz_gen = QuizGenerator()
perplexity_client = PerplexityClient(api_key=os.getenv('GROQ_API_KEY'))

@app.route('/admin')
def admin_dashboard():
    return render_template('admin.html')

@app.route('/api/admin/calendar', methods=['GET', 'POST'])
@admin_required
def admin_calendar():
    if request.method == 'POST':
        data = request.json
        db.add_schedule(
            data.get('type'),
            data.get('start'),
            data.get('end'),
            data.get('details'),
            data.get('is_exam', False)
        )
        return jsonify({'success': True})
    
    schedules = db.get_all_schedules()
    return jsonify({'success': True, 'schedules': schedules})

@app.route('/api/admin/events/pending', methods=['GET'])
@admin_required
def pending_events():
    proposals = db.get_all_proposals_for_admin()
    return jsonify({'success': True, 'events': proposals})

@app.route('/api/admin/events/approve', methods=['POST'])
@admin_required
def approve_event():
    data = request.json
    event_id = data.get('id')
    status = data.get('status')
    comment = data.get('comment', '').strip() or None
    if not event_id or not status:
        return jsonify({'error': 'id and status are required'}), 400
    db.update_event_status(event_id, status, admin_comment=comment)
    return jsonify({'success': True, 'id': event_id, 'status': status})

@app.route('/api/admin/release-tickets', methods=['POST'])
@admin_required
def release_tickets():
    data = request.json
    db.update_setting('hall_tickets_released', '1' if data.get('release') else '0')
    return jsonify({'success': True})

@app.route('/coordinator')
def coordinator_dashboard():
    return render_template('coordinator.html')

@app.route('/api/coordinator/club', methods=['GET', 'POST'])
def coordinator_club():
    coord_id = int(request.cookies.get('coord_id', 1))
    if request.method == 'POST':
        data = request.form
        logo_path = None
        if 'logo' in request.files and request.files['logo'].filename:
            logo_file = request.files['logo']
            logo_path = f"uploads/{logo_file.filename}"
            logo_file.save(os.path.join('frontend/static', logo_path))
        club_id = db.save_club_profile(
            data.get('name'), data.get('bio'), logo_path,
            data.get('instagram'), data.get('linkedin'), coord_id
        )
        members = []
        names = request.form.getlist('member_name[]')
        emails = request.form.getlist('member_email[]')
        for n, e in zip(names, emails):
            if n.strip():
                members.append({'name': n, 'email': e})
        db.save_club_members(club_id, members)
        return jsonify({'success': True, 'club_id': club_id})
    club = db.get_club_by_coordinator(coord_id) or {}
    if club:
        club['members'] = db.get_club_members(club['id'])
    return jsonify({'success': True, 'club': club})

@app.route('/api/coordinator/proposals', methods=['GET', 'POST'])
def coordinator_proposals():
    coord_id = int(request.cookies.get('coord_id', 1))
    club = db.get_club_by_coordinator(coord_id)
    if request.method == 'POST':
        if not club:
            return jsonify({'error': 'No club profile found. Please create one first.'}), 400
        data = request.form
        event_date = data.get('event_date')
        # Conflict check
        conflict = db.check_date_conflict(event_date)
        if conflict.get('conflict'):
            return jsonify({'error': f"Date conflict with: {conflict['desc']} ({conflict['start']} to {conflict['end']})"}), 409
        file_path = None
        if 'proposal_file' in request.files and request.files['proposal_file'].filename:
            f = request.files['proposal_file']
            safe_name = f.filename.replace(' ', '_')
            file_path = f"uploads/{safe_name}"
            f.save(os.path.join('frontend/static', file_path))
        status = 'Draft' if data.get('save_draft') else 'Pending'
        db.submit_proposal(
            club['id'], data.get('title'), data.get('description'),
            event_date, data.get('venue'), data.get('attendance', 0),
            data.get('budget_note'), file_path, status
        )
        return jsonify({'success': True, 'status': status})
    if not club:
        return jsonify({'success': True, 'proposals': []})
    proposals = db.get_proposals_by_club(club['id'])
    return jsonify({'success': True, 'proposals': proposals})

@app.route('/api/coordinator/conflict-check', methods=['GET'])
def conflict_check():
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date required'}), 400
    result = db.check_date_conflict(date)
    return jsonify(result)


@app.route('/seating')
def seating_dashboard():
    return render_template('seating.html')

@app.route('/api/seating/rooms', methods=['GET', 'POST'])
def seating_rooms():
    if request.method == 'POST':
        data = request.json
        rid = db.add_room(data['name'], int(data['capacity']), int(data.get('per_row', 2)))
        return jsonify({'success': True, 'id': rid})
    return jsonify({'success': True, 'rooms': db.get_all_rooms()})

@app.route('/api/seating/rooms/<int:room_id>', methods=['DELETE'])
def delete_seating_room(room_id):
    db.delete_room(room_id)
    return jsonify({'success': True})

@app.route('/api/seating/exams', methods=['GET', 'POST'])
def seating_exams():
    if request.method == 'POST':
        data = request.json
        eid = db.create_exam(data['name'], data.get('date'))
        return jsonify({'success': True, 'id': eid})
    return jsonify({'success': True, 'exams': db.get_all_exams()})

@app.route('/api/seating/students', methods=['GET', 'POST'])
def seating_students():
    if request.method == 'POST':
        data = request.json
        exam_id = data['exam_id']
        for s in data.get('students', []):
            db.add_exam_student(exam_id, s['name'], s['roll_no'],
                                s.get('department',''), s.get('subject',''))
        return jsonify({'success': True})
    exam_id = request.args.get('exam_id')
    students = db.get_exam_students(exam_id) if exam_id else []
    return jsonify({'success': True, 'students': students})

@app.route('/api/seating/students/import', methods=['POST'])
def seating_students_import():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    exam_id = request.form.get('exam_id')
    if not exam_id:
        return jsonify({'error': 'No exam selected'}), 400
    
    filename = file.filename.lower()
    try:
        content = file.read()
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            return jsonify({'error': 'Unsupported file format. Use CSV or Excel.'}), 400
        
        # Take a sample of the data to send to Grok for intelligent extraction
        # If the file is large, we process it in chunks or just send a sample if headers are needed
        # However, the user wants the AI to handle the registration.
        # Let's convert the entire (or first few hundred) rows to a string.
        data_sample = df.head(150).to_csv(index=False)
        
        prompt = f"""
        Extract student registration details from the following raw data.
        Return a valid JSON array of objects, where each object has:
        "name" (full name), "roll_no" (unique identification number/roll number), 
        "department" (branch/major, leave empty if not found), 
        "subject" (subject name, leave empty if not found).

        Format: [{{"name": "...", "roll_no": "...", "department": "...", "subject": "..."}}]
        
        Important: Return ONLY the JSON array. Do not include any text before or after.
        
        Raw Data (CSV format):
        {data_sample}
        """
        
        messages = [
            {"role": "system", "content": "You are a data extraction assistant specializing in student registration lists."},
            {"role": "user", "content": prompt}
        ]
        
        ai_response = perplexity_client.chat_completion(messages, model="llama-3.3-70b-versatile")
        raw_text = ai_response['choices'][0]['message']['content'].strip()
        
        # Clean potential markdown wrapping
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        students = json.loads(raw_text)
        
        students_added = 0
        for s in students:
            name = str(s.get('name', '')).strip()
            roll_no = str(s.get('roll_no', '')).strip()
            if not name or not roll_no: continue
            
            db.add_exam_student(exam_id, name, roll_no, 
                                s.get('department', ''), 
                                s.get('subject', ''))
            students_added += 1
            
        return jsonify({'success': True, 'count': students_added})
    except Exception as e:
        print(f"Import Error: {e}")
        return jsonify({'error': f"Error parsing file with AI: {str(e)}"}), 500

@app.route('/api/seating/generate', methods=['POST'])
def seating_generate():
    from backend.core.seating_algorithm import generate_seating
    data     = request.json
    exam_id  = data['exam_id']
    students = db.get_exam_students(exam_id)
    rooms    = db.get_all_rooms()
    if not students:
        return jsonify({'error': 'No students registered for this exam.'}), 400
    if not rooms:
        return jsonify({'error': 'No rooms configured. Please add rooms first.'}), 400
    assignments, error = generate_seating(students, rooms)
    if error:
        return jsonify({'error': error}), 409
    db.save_seating_assignments(exam_id, assignments)
    chart = db.get_seating_chart(exam_id)
    return jsonify({'success': True, 'chart': chart, 'total': len(assignments)})

@app.route('/api/seating/chart/<int:exam_id>', methods=['GET'])
def seating_chart(exam_id):
    chart = db.get_seating_chart(exam_id)
    return jsonify({'success': True, 'chart': chart})

@app.route('/api/seating/search', methods=['GET'])
def seating_search():
    exam_id  = request.args.get('exam_id')
    roll_no  = request.args.get('roll', '')
    result   = db.search_student_seat(exam_id, roll_no)
    return jsonify({'success': True, 'result': result})

@app.route('/api/seating/finalize', methods=['POST'])
def seating_finalize():
    data = request.json
    db.finalize_exam(data['exam_id'])
    return jsonify({'success': True})

@app.route('/api/settings/<key>', methods=['GET'])
def get_system_setting(key):
    value = db.get_setting(key)
    return jsonify({'success': True, 'value': value})

@app.route('/api/calendar', methods=['GET'])
def get_calendar():
    """Public endpoint for students to see the calendar"""
    schedules = db.get_all_schedules()
    return jsonify({'success': True, 'schedules': schedules})

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/student')
def index():
    return render_template('index.html')

@app.route('/api/start-topic', methods=['POST'])
def start_topic():
    data = request.json
    topic = data.get('topic')
    persona = data.get('persona', 'General')
    difficulty = data.get('difficulty', 'Intermediate')
    
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400
    
    session_id = request.cookies.get('session_id', os.urandom(16).hex())
    learning_session = LearningSession(persona=persona, difficulty=difficulty)
    
    try:
        roadmap = learning_session.start_new_topic(topic)
        sessions[session_id] = learning_session
        
        steps = [
            {
                'number': step['number'],
                'title': step['title'],
                'details': step['details']
            }
            for step in roadmap.steps
        ]
        
        # Save to database
        roadmap_data = {'topic': topic, 'steps': steps, 'persona': persona, 'difficulty': difficulty}
        topic_id = db.save_topic(topic, roadmap_data, len(steps))
        
        response = jsonify({
            'success': True,
            'topic': topic,
            'topic_id': topic_id,
            'steps': steps,
            'currentStep': 0
        })
        response.set_cookie('session_id', session_id)
        response.set_cookie('topic_id', str(topic_id))
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-guide', methods=['POST'])
def get_guide():
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    try:
        guide = learning_session.get_detailed_guide_for_step()
        return jsonify({
            'success': True,
            'guide': guide
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/next-step', methods=['POST'])
def next_step():
    session_id = request.cookies.get('session_id')
    topic_id = request.cookies.get('topic_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    step = learning_session.next_step()
    
    # Update progress in database
    if topic_id:
        db.update_topic_progress(int(topic_id), learning_session.current_step_index)
    
    if step:
        return jsonify({
            'success': True,
            'step': {
                'number': step['number'],
                'title': step['title'],
                'details': step['details']
            },
            'currentStepIndex': learning_session.current_step_index
        })
    else:
        return jsonify({
            'success': True,
            'completed': True,
            'message': 'You have completed the roadmap!'
        })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with persona awareness"""
    data = request.json
    message = data.get('message')
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    current_step = learning_session.get_current_step()
    
    try:
        persona_styles = {
            "General": "helpful and clear",
            "Scientist": "academic, precise, and highly technical",
            "ELI5": "extremely simple, using analogies that a 5-year-old would understand",
            "Socratic": "inquisitive, answering with questions that guide the user to discover the answer themselves"
        }
        style = persona_styles.get(learning_session.persona, "helpful")
        
        # Build context-aware prompt
        context = f"""You are a {learning_session.persona} learning assistant. Your teaching style is {style}.
The user is currently learning about:
Topic: {learning_session.roadmap.topic}
Difficulty: {learning_session.difficulty}
Current Step: {current_step['title']}

User question: {message}

Provide a clear, helpful answer in your assigned style ({style}) that relates to their current learning step."""
        
        messages = [{"role": "user", "content": context}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content']
        
        # Save to database
        if topic_id:
            db.save_chat_message(int(topic_id), learning_session.current_step_index, 'user', message)
            db.save_chat_message(int(topic_id), learning_session.current_step_index, 'assistant', ai_response)
        
        return jsonify({
            'success': True,
            'response': ai_response
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    """Generate a quiz for the current step"""
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    current_step = learning_session.get_current_step()
    
    try:
        step_details = '\n'.join(current_step['details']) if current_step['details'] else current_step['title']
        questions = quiz_gen.generate_quiz(
            learning_session.roadmap.topic,
            current_step['title'],
            step_details
        )
        
        return jsonify({
            'success': True,
            'questions': questions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-quiz', methods=['POST'])
def submit_quiz():
    """Submit quiz answers and get score"""
    data = request.json
    answers = data.get('answers', {})
    questions = data.get('questions', [])
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    # Calculate score
    correct = 0
    results = []
    
    for i, question in enumerate(questions):
        user_answer = answers.get(str(i))
        is_correct = quiz_gen.check_answer(question, user_answer) if user_answer else False
        
        if is_correct:
            correct += 1
        
        results.append({
            'question_number': i + 1,
            'correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': question['correct']
        })
    
    # Save to database
    if topic_id:
        db.save_quiz_result(int(topic_id), learning_session.current_step_index, correct, len(questions))
    
    return jsonify({
        'success': True,
        'score': correct,
        'total': len(questions),
        'percentage': round((correct / len(questions)) * 100) if questions else 0,
        'results': results
    })

@app.route('/api/save-note', methods=['POST'])
def save_note():
    """Save a note for the current step"""
    data = request.json
    content = data.get('content')
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    if topic_id:
        db.save_note(int(topic_id), learning_session.current_step_index, content)
    
    return jsonify({'success': True})

@app.route('/api/get-note', methods=['GET'])
def get_note():
    """Get note for current step"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    if topic_id:
        note = db.get_note(int(topic_id), learning_session.current_step_index)
        return jsonify({'success': True, 'note': note})
    
    return jsonify({'success': True, 'note': None})

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """Get all topics"""
    topics = db.get_all_topics()
    return jsonify({'success': True, 'topics': topics})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get learning statistics"""
    topics = db.get_all_topics()
    total_topics = len(topics)
    completed_topics = len([t for t in topics if t['completed']])
    
    # Calculate total steps across all topics
    total_steps = sum([t['total_steps'] for t in topics])
    current_steps = sum([t['current_step'] + 1 for t in topics]) # +1 because current_step is 0-indexed
    
    return jsonify({
        'success': True,
        'totalTopics': total_topics,
        'completedTopics': completed_topics,
        'progress': round((current_steps / total_steps) * 100) if total_steps > 0 else 0
    })

@app.route('/api/export', methods=['GET'])
def export_handbook():
    """Export the current learning session as a Markdown handbook"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return "No active session found.", 400
    
    learning_session = sessions[session_id]
    topic_data = db.get_topic(int(topic_id))
    
    if not topic_data:
        return "Topic not found.", 404
    
    md_content = f"# Learning Handbook: {topic_data['name']}\n"
    md_content += f"**Persona:** {learning_session.persona} | **Difficulty:** {learning_session.difficulty}\n\n"
    md_content += "## Roadmap\n"
    for i, step in enumerate(topic_data['roadmap_data']['steps']):
        md_content += f"### Step {i+1}: {step['title']}\n"
        for detail in step['details']:
            md_content += f"- {detail}\n"
        
        # Add Note
        note = db.get_note(int(topic_id), i)
        if note:
            md_content += f"\n#### My Notes\n> {note}\n"
        
        # Add Chat History
        chat_history = db.get_chat_history(int(topic_id), i)
        if chat_history:
            md_content += f"\n#### Chat History\n"
            for msg in chat_history:
                md_content += f"**{msg['role'].capitalize()}:** {msg['message']}\n\n"
        
        md_content += "\n---\n"
    
    response = make_response(md_content)
    response.headers["Content-Disposition"] = f"attachment; filename={topic_data['name'].replace(' ', '_')}_Handook.md"
    response.headers["Content-Type"] = "text/markdown"
    return response

@app.route('/api/chat-history', methods=['GET'])
def get_chat_history():
    """Get chat history for current step"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    if topic_id:
        history = db.get_chat_history(int(topic_id), learning_session.current_step_index)
        return jsonify({'success': True, 'history': history})
    
    return jsonify({'success': True, 'history': []})

@app.route('/api/get-resources', methods=['POST'])
def get_resources():
    """Fetch related learning resources for the current step"""
    data = request.json
    topic = data.get('topic')
    step_title = data.get('step')
    
    if not topic or not step_title:
        return jsonify({'error': 'Topic and step title are required'}), 400
    
    try:
        # Ask AI for resource titles and types ONLY — no URLs (AI hallucinates URLs)
        prompt = f"""Suggest 4 learning resource titles for someone studying "{step_title}" in the context of "{topic}".
Return ONLY a JSON array. Each object must have:
- "title": a descriptive search phrase (e.g. "Python Variables Tutorial for Beginners")
- "type": one of "Video", "Article", "Course", or "Practice"

Example format:
[
  {{"title": "...", "type": "Video"}},
  {{"title": "...", "type": "Article"}},
  {{"title": "...", "type": "Course"}},
  {{"title": "...", "type": "Practice"}}
]

Return ONLY the JSON array. No explanation, no markdown."""

        messages = [{"role": "user", "content": prompt}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content'].strip()

        # Strip any markdown code fences
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()

        suggestions = json.loads(ai_response)

        # Build guaranteed-working search URLs on trusted platforms
        import urllib.parse

        def build_url(title, rtype):
            q = urllib.parse.quote_plus(title)
            if rtype == "Video":
                return f"https://www.youtube.com/results?search_query={q}"
            elif rtype == "Course":
                return f"https://www.coursera.org/search?query={q}"
            elif rtype == "Practice":
                return f"https://www.freecodecamp.org/news/search/?query={q}"
            else:  # Article / default
                return f"https://www.google.com/search?q={q}"

        resources = []
        for s in suggestions[:4]:
            title = s.get('title', f'{step_title} tutorial')
            rtype = s.get('type', 'Article')
            resources.append({
                'title': title,
                'type': rtype,
                'url': build_url(title, rtype)
            })

        return jsonify({'success': True, 'resources': resources})

    except Exception as e:
        # Fallback: build search links directly without AI
        import urllib.parse
        q = urllib.parse.quote_plus(f"{topic} {step_title}")
        return jsonify({
            'success': True,
            'resources': [
                {'title': f'{step_title} — Video Tutorial', 'type': 'Video',
                 'url': f'https://www.youtube.com/results?search_query={q}'},
                {'title': f'{step_title} — Written Guide',  'type': 'Article',
                 'url': f'https://www.google.com/search?q={q}'},
                {'title': f'{step_title} — Online Course',  'type': 'Course',
                 'url': f'https://www.coursera.org/search?query={q}'},
                {'title': f'{step_title} — Practice',       'type': 'Practice',
                 'url': f'https://www.freecodecamp.org/news/search/?query={q}'},
            ]
        })

@app.route('/api/clear-chat', methods=['POST'])
def clear_chat():
    """Clear chat history for current step"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    if topic_id:
        db.clear_chat_history(int(topic_id), learning_session.current_step_index)
        return jsonify({'success': True})
    
    return jsonify({'error': 'No topic selected'}), 400


@app.route('/api/student/verify-ticket', methods=['POST'])
def verify_hall_ticket():
    data = request.json
    roll_no = data.get('roll_no', '').strip()
    
    # Check if released
    released = db.get_setting('hall_tickets_released')
    if released != '1':
        return jsonify({'error': 'Hall tickets have not been released yet.'}), 403
        
    info = db.get_student_ticket_info(roll_no)
    if not info:
        return jsonify({'error': 'Invalid Roll Number or Student not found in any finalized exam.'}), 404
        
    return jsonify({'success': True, 'info': info})

@app.route('/api/student/download-ticket', methods=['GET'])
def download_hall_ticket():
    roll_no = request.args.get('roll_no')
    if not roll_no:
        return "Roll Number is required.", 400
        
    released = db.get_setting('hall_tickets_released')
    if released != '1':
        return "Hall tickets not released.", 403
        
    info = db.get_student_ticket_info(roll_no)
    if not info:
        return "Ticket info not found.", 404
        
    # Generate a simple formatted Markdown/Text hall ticket
    content = f"""
# HALL TICKET: {info['exam_name']}
--------------------------------------------------
STUDENT DETAILS
Name: {info['name']}
Roll No: {info['roll_no']}
Department: {info['department']}
Subject: {info['subject']}
--------------------------------------------------
EXAM DETAILS
Date: {info['exam_date']}
--------------------------------------------------
SEATING INFO
Room: {info['room']}
Row: {info['row']}
Seat/Bench No: {info['col']}
--------------------------------------------------
IMPORTANT INSTRUCTIONS:
1. Please carry this hall ticket to the examination hall.
2. Reach the venue 15 minutes before the start time.
3. No electronic gadgets allowed.
--------------------------------------------------
Generated by Digital Campus Hub (DCH)
"""
    response = make_response(content)
    response.headers["Content-Disposition"] = f"attachment; filename=HallTicket_{roll_no}.txt"
    response.headers["Content-Type"] = "text/plain"
    return response

@app.route('/hall-ticket/mobile/<roll_no>')
def mobile_hall_ticket(roll_no):
    released = db.get_setting('hall_tickets_released')
    if released != '1':
        return "Hall tickets have not been released by the admin yet.", 403
        
    info = db.get_student_ticket_info(roll_no)
    if not info:
        return "Hall ticket not found. Please verify your roll number.", 404
        
    return render_template('mobile_ticket.html', info=info)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(host=host, port=port, debug=debug)
