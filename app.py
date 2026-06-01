from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

app = Flask(__name__)

# DATABASE SETUP
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['worknest']

jobs_col        = db['jobs']
employers_col   = db['employers']
candidates_col  = db['candidates']
applications_col = db['applications']

# HELPER
def s(doc):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

def now():
    return datetime.utcnow().isoformat()

STATUS_MESSAGES = {
    'applied':   "Application received! We'll be in touch soon 🤞",
    'reviewed':  "Your profile is being reviewed — fingers crossed! 👀",
    'interview': "You're in! They want to meet you 🎉",
    'hired':     "Congratulations, you got the job! 🥳",
    'rejected':  "Not this time, but keep going — the right role is out there 💪"
}



# FRONTEND

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/employer')
def employer():
    return render_template('employer.html')

@app.route('/candidate')
def candidate():
    return render_template('candidate.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')





#  EMPLOYER APIs

@app.route('/api/employers/register', methods=['POST'])
def register_employer():
    d = request.get_json()
    if not all(k in d for k in ['company_name', 'email', 'password']):
        return jsonify({'error': 'company_name, email and password are required'}), 400
    if employers_col.find_one({'email': d['email']}):
        return jsonify({'error': 'This email is already registered'}), 409
    result = employers_col.insert_one({
        'company_name': d['company_name'],
        'email':        d['email'],
        'password':     d['password'],
        'website':      d.get('website', ''),
        'description':  d.get('description', ''),
        'industry':     d.get('industry', ''),
        'created_at':   now()
    })
    return jsonify({'message': f"Welcome to WorkNest, {d['company_name']}! 🎉", 'id': str(result.inserted_id)}), 201

@app.route('/api/employers/login', methods=['POST'])
def login_employer():
    d = request.get_json()
    emp = employers_col.find_one({'email': d.get('email'), 'password': d.get('password')})
    if not emp:
        return jsonify({'error': 'Wrong email or password'}), 401
    return jsonify({'message': 'Welcome back!', 'employer_id': str(emp['_id']), 'company_name': emp['company_name']})

@app.route('/api/employers', methods=['GET'])
def get_employers():
    emps = [s(e) for e in employers_col.find({}, {'password': 0})]
    return jsonify(emps)


#  JOB APIs

@app.route('/api/jobs', methods=['POST'])
def post_job():
    d = request.get_json()
    if not all(k in d for k in ['title', 'employer_id', 'description', 'location', 'job_type', 'salary']):
        return jsonify({'error': 'Missing required fields'}), 400
    result = jobs_col.insert_one({
        'title':        d['title'],
        'employer_id':  d['employer_id'],
        'company_name': d.get('company_name', ''),
        'description':  d['description'],
        'location':     d['location'],
        'job_type':     d['job_type'],
        'salary':       d['salary'],
        'skills':       d.get('skills', []),
        'experience':   d.get('experience', 'Any'),
        'status':       'open',
        'posted_at':    now()
    })
    return jsonify({'message': 'Job posted! Candidates can now apply 🚀', 'job_id': str(result.inserted_id)}), 201

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    query = {'status': 'open'}
    keyword  = request.args.get('keyword', '')
    location = request.args.get('location', '')
    job_type = request.args.get('job_type', '')
    if keyword:
        query['$or'] = [
            {'title':        {'$regex': keyword, '$options': 'i'}},
            {'description':  {'$regex': keyword, '$options': 'i'}},
            {'company_name': {'$regex': keyword, '$options': 'i'}}
        ]
    if location:
        query['location'] = {'$regex': location, '$options': 'i'}
    if job_type:
        query['job_type'] = job_type
    return jsonify([s(j) for j in jobs_col.find(query).sort('posted_at', -1)])

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    job = jobs_col.find_one({'_id': ObjectId(job_id)})
    return jsonify(s(job)) if job else (jsonify({'error': 'Job not found'}), 404)

@app.route('/api/jobs/<job_id>', methods=['PUT'])
def update_job(job_id):
    d = request.get_json()
    d.pop('_id', None)
    jobs_col.update_one({'_id': ObjectId(job_id)}, {'$set': d})
    return jsonify({'message': 'Job updated!'})

@app.route('/api/jobs/<job_id>', methods=['DELETE'])
def close_job(job_id):
    jobs_col.update_one({'_id': ObjectId(job_id)}, {'$set': {'status': 'closed'}})
    return jsonify({'message': 'Job closed.'})



#  CANDIDATE APIs
@app.route('/api/candidates/register', methods=['POST'])
def register_candidate():
    d = request.get_json()
    if not all(k in d for k in ['name', 'email', 'password']):
        return jsonify({'error': 'name, email and password are required'}), 400
    if candidates_col.find_one({'email': d['email']}):
        return jsonify({'error': 'This email is already registered'}), 409
    result = candidates_col.insert_one({
        'name':        d['name'],
        'email':       d['email'],
        'password':    d['password'],
        'skills':      d.get('skills', []),
        'experience':  d.get('experience', ''),
        'resume_text': d.get('resume_text', ''),
        'location':    d.get('location', ''),
        'created_at':  now()
    })
    return jsonify({'message': f"You're on WorkNest now, {d['name']}! Go get that job 💪", 'id': str(result.inserted_id)}), 201

@app.route('/api/candidates/login', methods=['POST'])
def login_candidate():
    d = request.get_json()
    c = candidates_col.find_one({'email': d.get('email'), 'password': d.get('password')})
    if not c:
        return jsonify({'error': 'Wrong email or password'}), 401
    return jsonify({'message': f"Hey {c['name']}! Good to see you 👋", 'candidate_id': str(c['_id']), 'name': c['name']})

@app.route('/api/candidates/<candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    d = request.get_json()
    d.pop('_id', None)
    candidates_col.update_one({'_id': ObjectId(candidate_id)}, {'$set': d})
    return jsonify({'message': 'Profile updated!'})

@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    cs = [s(c) for c in candidates_col.find({}, {'password': 0})]
    return jsonify(cs)

# ══════════════════════════════════════════════════════════════
#  APPLICATION APIs
# ══════════════════════════════════════════════════════════════

@app.route('/api/apply', methods=['POST'])
def apply():
    d = request.get_json()
    if not all(k in d for k in ['job_id', 'candidate_id', 'cover_letter']):
        return jsonify({'error': 'job_id, candidate_id and cover_letter required'}), 400
    if applications_col.find_one({'job_id': d['job_id'], 'candidate_id': d['candidate_id']}):
        return jsonify({'error': "You've already applied for this job!"}), 409
    candidate = candidates_col.find_one({'_id': ObjectId(d['candidate_id'])})
    job       = jobs_col.find_one({'_id': ObjectId(d['job_id'])})
    if not candidate or not job:
        return jsonify({'error': 'Invalid candidate or job ID'}), 404
    result = applications_col.insert_one({
        'job_id':          d['job_id'],
        'job_title':       job['title'],
        'company_name':    job['company_name'],
        'employer_id':     job['employer_id'],
        'candidate_id':    d['candidate_id'],
        'candidate_name':  candidate['name'],
        'candidate_email': candidate['email'],
        'cover_letter':    d['cover_letter'],
        'status':          'applied',
        'status_message':  STATUS_MESSAGES['applied'],
        'employer_feedback': '',
        'applied_at':      now()
    })
    return jsonify({'message': STATUS_MESSAGES['applied'], 'application_id': str(result.inserted_id)}), 201

@app.route('/api/applications/candidate/<candidate_id>', methods=['GET'])
def my_applications(candidate_id):
    apps = [s(a) for a in applications_col.find({'candidate_id': candidate_id}).sort('applied_at', -1)]
    return jsonify(apps)

@app.route('/api/applications/job/<job_id>', methods=['GET'])
def job_applications(job_id):
    apps = [s(a) for a in applications_col.find({'job_id': job_id}).sort('applied_at', -1)]
    return jsonify(apps)

@app.route('/api/applications/<app_id>/status', methods=['PUT'])
def update_status(app_id):
    d = request.get_json()
    status = d.get('status')
    valid  = ['applied', 'reviewed', 'interview', 'hired', 'rejected']
    if status not in valid:
        return jsonify({'error': f'Status must be one of {valid}'}), 400
    applications_col.update_one(
        {'_id': ObjectId(app_id)},
        {'$set': {
            'status':           status,
            'status_message':   STATUS_MESSAGES[status],
            'employer_feedback': d.get('feedback', ''),
        }}
    )
    return jsonify({'message': f'Updated! Candidate will see: "{STATUS_MESSAGES[status]}"'})

@app.route('/api/applications/<app_id>', methods=['DELETE'])
def withdraw(app_id):
    applications_col.delete_one({'_id': ObjectId(app_id)})
    return jsonify({'message': 'Application withdrawn.'})

@app.route('/api/applications', methods=['GET'])
def all_applications():
    apps = [s(a) for a in applications_col.find().sort('applied_at', -1)]
    return jsonify(apps)


@app.route('/api/stats', methods=['GET'])
def stats():
    return jsonify({
        'total_jobs':         jobs_col.count_documents({'status': 'open'}),
        'total_employers':    employers_col.count_documents({}),
        'total_candidates':   candidates_col.count_documents({}),
        'total_applications': applications_col.count_documents({}),
        'hired':              applications_col.count_documents({'status': 'hired'}),
        'interviews':         applications_col.count_documents({'status': 'interview'}),
    })

if __name__ == '__main__':
    app.run(debug=True)
