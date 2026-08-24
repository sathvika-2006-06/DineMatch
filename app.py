from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import string
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===================== DATABASE MODELS =====================

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_code = db.Column(db.String(10), unique=True, nullable=False)
    group_name = db.Column(db.String(100), nullable=False)
    member_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('Member', backref='group', lazy=True, cascade='all, delete-orphan')
    restaurants = db.relationship('Restaurant', secondary='group_restaurants', backref='groups')
    votes = db.relationship('Vote', backref='group', lazy=True, cascade='all, delete-orphan')

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.String(50), nullable=False)  # e.g., "200-300"
    cuisine = db.Column(db.String(500), nullable=False)  # JSON string
    food_type = db.Column(db.String(50), nullable=False)
    restaurant_type = db.Column(db.String(100), nullable=False)  # JSON string
    dietary_requirement = db.Column(db.String(100), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    votes = db.relationship('Vote', backref='member', lazy=True)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    cuisine = db.Column(db.String(500), nullable=False)  # JSON string
    cost = db.Column(db.Integer, nullable=False)  # Average cost per person
    rating = db.Column(db.Float, default=4.0)
    food_type = db.Column(db.String(100), nullable=False)  # veg, non-veg, vegan, any
    restaurant_type = db.Column(db.String(100), nullable=False)  # cafe, restaurant, fastfood, buffet, any
    dietary_options = db.Column(db.String(500), nullable=False)  # JSON string
    mood = db.Column(db.String(100), nullable=False)  # casual, party, family, studybreak, any
    description = db.Column(db.String(500), nullable=False)
    
    votes = db.relationship('Vote', backref='restaurant', lazy=True)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Association table for group-restaurant recommendations
group_restaurants = db.Table('group_restaurants',
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
    db.Column('restaurant_id', db.Integer, db.ForeignKey('restaurant.id'))
)

# ===================== HELPER FUNCTIONS =====================

def generate_group_code():
    """Generate unique group code like DM4821"""
    while True:
        code = 'DM' + ''.join(random.choices(string.digits, k=4))
        if not Group.query.filter_by(group_code=code).first():
            return code

def get_budget_range(budget_str):
    """Convert budget string to numeric range"""
    ranges = {
        '100-200': (100, 200),
        '200-300': (200, 300),
        '300-500': (300, 500),
        '500+': (500, 10000)
    }
    return ranges.get(budget_str, (100, 10000))

def parse_json_string(json_str):
    """Safely parse JSON string, return list"""
    if isinstance(json_str, str):
        try:
            import json
            return json.loads(json_str)
        except:
            return [json_str]
    return json_str if isinstance(json_str, list) else [json_str]

def calculate_match_score(restaurant, member_preferences):
    """Calculate compatibility score for a single member"""
    score = 0
    
    # Parse preferences
    member_cuisines = parse_json_string(member_preferences.get('cuisine', '[]'))
    member_rest_types = parse_json_string(member_preferences.get('restaurant_type', '[]'))
    
    # Cuisine match - 30 points
    restaurant_cuisines = parse_json_string(restaurant.cuisine)
    cuisine_match = any(c.lower() in [m.lower() for m in member_cuisines] for c in restaurant_cuisines)
    if cuisine_match:
        score += 30
    
    # Budget match - 25 points
    min_budget, max_budget = get_budget_range(member_preferences.get('budget', '100-200'))
    if min_budget <= restaurant.cost <= max_budget:
        score += 25
    
    # Food type match - 20 points
    member_food_type = member_preferences.get('food_type', 'Any')
    if member_food_type.lower() == 'any' or member_food_type.lower() == restaurant.food_type.lower():
        score += 20
    
    # Restaurant type match - 10 points
    restaurant_types = parse_json_string(restaurant.restaurant_type)
    rest_type_match = any(t.lower() in [m.lower() for m in member_rest_types] for t in restaurant_types) if member_rest_types else True
    if rest_type_match or 'Any' in member_rest_types:
        score += 10
    
    # Rating match - 10 points
    score += min(10, (restaurant.rating / 5.0) * 10)
    
    # Mood match - 5 points
    member_mood = member_preferences.get('mood', 'Any')
    if member_mood.lower() == 'any' or member_mood.lower() in [m.lower() for m in parse_json_string(restaurant.mood)]:
        score += 5
    
    return score

def calculate_group_match(restaurant, all_members):
    """Calculate group match score"""
    if not all_members:
        return 0
    
    individual_scores = []
    for member in all_members:
        member_prefs = {
            'cuisine': member.cuisine,
            'budget': member.budget,
            'food_type': member.food_type,
            'restaurant_type': member.restaurant_type,
            'mood': member.mood
        }
        score = calculate_match_score(restaurant, member_prefs)
        individual_scores.append(score)
    
    # Group score is the minimum of individual scores (fairness approach)
    # Or average - let's use average for better results
    return sum(individual_scores) / len(individual_scores) if individual_scores else 0

def get_ai_explanation(group_summary, restaurants_info):
    """Get AI explanation using Gemini API"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return None
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Based on the following group preferences and restaurant information, 
        provide a brief (2-3 sentence) explanation of why the top restaurant is recommended:
        
        Group Preferences:
        {group_summary}
        
        Top Restaurant Info:
        {restaurants_info}
        
        Keep the explanation friendly and concise.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except:
        return None

# ===================== ROUTES =====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    """Create new group"""
    if request.method == 'POST':
        data = request.json
        group_name = data.get('group_name', '').strip()
        member_count = int(data.get('member_count', 0))
        
        if not group_name or member_count <= 0:
            return jsonify({'error': 'Invalid input'}), 400
        
        group_code = generate_group_code()
        new_group = Group(
            group_code=group_code,
            group_name=group_name,
            member_count=member_count
        )
        
        db.session.add(new_group)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'group_code': group_code,
            'group_id': new_group.id
        })
    
    return render_template('create_group.html')

@app.route('/join_group', methods=['GET', 'POST'])
def join_group():
    """Join existing group"""
    if request.method == 'POST':
        data = request.json
        group_code = data.get('group_code', '').strip().upper()
        name = data.get('name', '').strip()
        
        group = Group.query.filter_by(group_code=group_code).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 400
        
        # Check if group has space
        member_count = Member.query.filter_by(group_id=group.id).count()
        if member_count >= group.member_count:
            return jsonify({'error': 'Group is full'}), 400
        
        session['group_id'] = group.id
        session['member_name'] = name
        
        return jsonify({'success': True, 'group_id': group.id})
    
    return render_template('join_group.html')

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    """Enter member preferences"""
    if request.method == 'POST':
        data = request.json
        group_id = session.get('group_id')
        name = session.get('member_name')
        
        if not group_id or not name:
            return jsonify({'error': 'Session expired'}), 400
        
        import json
        new_member = Member(
            group_id=group_id,
            name=name,
            budget=data.get('budget', ''),
            cuisine=json.dumps(data.get('cuisine', [])),
            food_type=data.get('food_type', ''),
            restaurant_type=json.dumps(data.get('restaurant_type', [])),
            dietary_requirement=data.get('dietary_requirement', ''),
            mood=data.get('mood', '')
        )
        
        db.session.add(new_member)
        db.session.commit()
        
        return jsonify({'success': True, 'group_id': group_id})
    
    group_id = session.get('group_id')
    if not group_id:
        return redirect(url_for('index'))
    
    group = Group.query.get(group_id)
    member_count = Member.query.filter_by(group_id=group_id).count()
    
    return render_template('preferences.html', 
                         group_name=group.group_name,
                         current_members=member_count,
                         total_members=group.member_count)

@app.route('/group/<int:group_id>/summary')
def group_summary(group_id):
    """Show group preference summary"""
    group = Group.query.get_or_404(group_id)
    members = Member.query.filter_by(group_id=group_id).all()
    
    return render_template('group_summary.html', group=group, members=members)

@app.route('/group/<int:group_id>/recommendations')
def recommendations(group_id):
    """Show restaurant recommendations"""
    group = Group.query.get_or_404(group_id)
    members = Member.query.filter_by(group_id=group_id).all()
    restaurants = Restaurant.query.all()
    
    # Calculate scores for all restaurants
    scored_restaurants = []
    for restaurant in restaurants:
        group_score = calculate_group_match(restaurant, members)
        
        # Calculate individual scores
        individual_scores = []
        for member in members:
            member_prefs = {
                'cuisine': member.cuisine,
                'budget': member.budget,
                'food_type': member.food_type,
                'restaurant_type': member.restaurant_type,
                'mood': member.mood
            }
            score = calculate_match_score(restaurant, member_prefs)
            individual_scores.append({
                'name': member.name,
                'score': score,
                'percentage': (score / 100) * 100
            })
        
        scored_restaurants.append({
            'restaurant': restaurant,
            'group_score': group_score,
            'group_percentage': (group_score / 100) * 100,
            'individual_scores': individual_scores
        })
    
    # Sort by group score
    scored_restaurants.sort(key=lambda x: x['group_score'], reverse=True)
    top_5 = scored_restaurants[:5]
    
    return render_template('recommendations.html', 
                         group=group,
                         restaurants=top_5)

@app.route('/group/<int:group_id>/voting')
def voting(group_id):
    """Voting page"""
    group = Group.query.get_or_404(group_id)
    members = Member.query.filter_by(group_id=group_id).all()
    restaurants = Restaurant.query.all()
    
    return render_template('voting.html', 
                         group=group,
                         members=members,
                         restaurants=restaurants)

@app.route('/group/<int:group_id>/vote', methods=['POST'])
def vote(group_id):
    """Record a vote"""
    data = request.json
    member_id = data.get('member_id')
    restaurant_id = data.get('restaurant_id')
    
    # Check if already voted
    existing = Vote.query.filter_by(group_id=group_id, member_id=member_id).first()
    if existing:
        return jsonify({'error': 'Already voted'}), 400
    
    new_vote = Vote(
        group_id=group_id,
        member_id=member_id,
        restaurant_id=restaurant_id
    )
    
    db.session.add(new_vote)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/group/<int:group_id>/result')
def result(group_id):
    """Final result page"""
    group = Group.query.get_or_404(group_id)
    members = Member.query.filter_by(group_id=group_id).all()
    
    # Get voting results
    votes = db.session.query(Vote.restaurant_id, db.func.count(Vote.id)).filter_by(group_id=group_id).group_by(Vote.restaurant_id).all()
    
    if not votes:
        winner = None
    else:
        winner_id = max(votes, key=lambda x: x[1])[0]
        winner = Restaurant.query.get(winner_id)
    
    # Calculate voting breakdown
    vote_counts = {restaurant_id: count for restaurant_id, count in votes}
    
    return render_template('result.html',
                         group=group,
                         winner=winner,
                         members=members,
                         vote_counts=vote_counts)

@app.route('/split_bill', methods=['GET', 'POST'])
def split_bill():
    """Split bill calculator"""
    if request.method == 'POST':
        data = request.json
        total = float(data.get('total', 0))
        members = int(data.get('members', 1))
        tip = float(data.get('tip', 0))
        
        if members <= 0:
            return jsonify({'error': 'Invalid number of members'}), 400
        
        final_amount = total + tip
        per_person = final_amount / members
        
        return jsonify({
            'success': True,
            'per_person': round(per_person, 2),
            'total': round(final_amount, 2)
        })
    
    return render_template('split_bill.html')

@app.route('/api/group/<int:group_id>/members-count')
def get_members_count(group_id):
    """Get number of members joined"""
    count = Member.query.filter_by(group_id=group_id).count()
    group = Group.query.get(group_id)
    return jsonify({'current': count, 'total': group.member_count})

@app.route('/api/group/<int:group_id>/votes')
def get_votes(group_id):
    """Get current vote counts"""
    votes = db.session.query(Vote.restaurant_id, db.func.count(Vote.id)).filter_by(group_id=group_id).group_by(Vote.restaurant_id).all()
    
    result = {}
    for restaurant_id, count in votes:
        restaurant = Restaurant.query.get(restaurant_id)
        result[restaurant.name] = count
    
    return jsonify(result)

# ===================== INITIALIZE DATABASE =====================

def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        db.create_all()
        
        # Check if restaurants already exist
        if Restaurant.query.first():
            return
        
        import json
        
        # Sample restaurant data
        restaurants_data = [
            # Indian Restaurants
            {
                'name': 'Paradise Restaurant',
                'cuisine': json.dumps(['Indian']),
                'cost': 250,
                'rating': 4.5,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Restaurant']),
                'dietary_options': json.dumps(['Vegetarian', 'Vegan', 'Jain']),
                'mood': json.dumps(['Family', 'Casual']),
                'description': 'Authentic North Indian cuisine with excellent ambiance'
            },
            {
                'name': 'Spice Hub',
                'cuisine': json.dumps(['Indian', 'Chinese']),
                'cost': 200,
                'rating': 4.2,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Restaurant']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian']),
                'mood': json.dumps(['Casual', 'Party']),
                'description': 'Fusion Indian and Chinese with great service'
            },
            {
                'name': 'Idli Paradise',
                'cuisine': json.dumps(['South Indian']),
                'cost': 150,
                'rating': 4.0,
                'food_type': 'veg',
                'restaurant_type': json.dumps(['Cafe', 'Restaurant']),
                'dietary_options': json.dumps(['Vegetarian', 'Vegan', 'Jain']),
                'mood': json.dumps(['Casual', 'Study Break']),
                'description': 'Fresh South Indian breakfast and snacks'
            },
            {
                'name': 'Bukhara Biryani',
                'cuisine': json.dumps(['Indian']),
                'cost': 300,
                'rating': 4.6,
                'food_type': 'non-veg',
                'restaurant_type': json.dumps(['Restaurant']),
                'dietary_options': json.dumps(['Non-Vegetarian', 'Vegetarian']),
                'mood': json.dumps(['Party', 'Family']),
                'description': 'Premium biryani and kebabs'
            },
            # Chinese Restaurants
            {
                'name': 'Chinese Garden',
                'cuisine': json.dumps(['Chinese']),
                'cost': 200,
                'rating': 4.3,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Restaurant']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan']),
                'mood': json.dumps(['Casual', 'Family']),
                'description': 'Authentic Chinese with modern twist'
            },
            {
                'name': 'Dragon Wok',
                'cuisine': json.dumps(['Chinese']),
                'cost': 180,
                'rating': 4.1,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Fast Food', 'Restaurant']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian']),
                'mood': json.dumps(['Casual', 'Study Break']),
                'description': 'Quick Chinese bites and full meals'
            },
            # Italian Restaurants
            {
                'name': 'Pizza Corner',
                'cuisine': json.dumps(['Italian']),
                'cost': 220,
                'rating': 4.2,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Fast Food', 'Cafe']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan']),
                'mood': json.dumps(['Casual', 'Study Break', 'Party']),
                'description': 'Wood-fired pizzas and Italian classics'
            },
            {
                'name': 'Pasta Vault',
                'cuisine': json.dumps(['Italian']),
                'cost': 280,
                'rating': 4.4,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Restaurant']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan', 'Gluten Free']),
                'mood': json.dumps(['Family', 'Party']),
                'description': 'Handmade pastas and romantic ambiance'
            },
            # Mexican Restaurants
            {
                'name': 'Taco Fiesta',
                'cuisine': json.dumps(['Mexican']),
                'cost': 200,
                'rating': 4.1,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Fast Food', 'Casual']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan']),
                'mood': json.dumps(['Casual', 'Party']),
                'description': 'Authentic Mexican street food'
            },
            {
                'name': 'Burrito Barn',
                'cuisine': json.dumps(['Mexican']),
                'cost': 180,
                'rating': 4.0,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Fast Food']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian']),
                'mood': json.dumps(['Casual', 'Study Break']),
                'description': 'Fresh burritos and bowls'
            },
            # Fast Food Chains
            {
                'name': 'Burger Bliss',
                'cuisine': json.dumps(['Fast Food']),
                'cost': 150,
                'rating': 3.9,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Fast Food']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan']),
                'mood': json.dumps(['Casual', 'Study Break']),
                'description': 'Quick bites and comfort food'
            },
            {
                'name': 'Fried Chicken Co',
                'cuisine': json.dumps(['Fast Food']),
                'cost': 120,
                'rating': 3.8,
                'food_type': 'non-veg',
                'restaurant_type': json.dumps(['Fast Food']),
                'dietary_options': json.dumps(['Non-Vegetarian']),
                'mood': json.dumps(['Casual', 'Study Break']),
                'description': 'Crispy fried chicken and sides'
            },
            {
                'name': 'Sandwich Studio',
                'cuisine': json.dumps(['Fast Food']),
                'cost': 100,
                'rating': 3.7,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Fast Food', 'Cafe']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan']),
                'mood': json.dumps(['Study Break', 'Casual']),
                'description': 'Fresh sandwiches and wraps'
            },
            # Premium Restaurants
            {
                'name': 'Posh Dining Club',
                'cuisine': json.dumps(['Indian', 'Continental']),
                'cost': 450,
                'rating': 4.7,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Restaurant']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan', 'Gluten Free', 'Jain']),
                'mood': json.dumps(['Party', 'Family']),
                'description': 'Fine dining with exquisite service'
            },
            {
                'name': 'Deluxe Buffet Palace',
                'cuisine': json.dumps(['Indian', 'Chinese', 'Italian']),
                'cost': 350,
                'rating': 4.3,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Buffet']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian']),
                'mood': json.dumps(['Family', 'Party']),
                'description': 'All-you-can-eat with variety'
            },
            # Cafes
            {
                'name': 'Coffee Corner Cafe',
                'cuisine': json.dumps(['Cafe']),
                'cost': 100,
                'rating': 4.0,
                'food_type': 'veg',
                'restaurant_type': json.dumps(['Cafe']),
                'dietary_options': json.dumps(['Vegetarian', 'Vegan', 'Lactose Free']),
                'mood': json.dumps(['Study Break', 'Casual']),
                'description': 'Cozy cafe with great coffee and pastries'
            },
            {
                'name': 'Brew & Bite',
                'cuisine': json.dumps(['Cafe']),
                'cost': 120,
                'rating': 4.1,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Cafe']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan', 'Gluten Free']),
                'mood': json.dumps(['Study Break', 'Casual']),
                'description': 'Modern cafe with healthy options'
            },
            # More variety
            {
                'name': 'Thali Express',
                'cuisine': json.dumps(['Indian']),
                'cost': 180,
                'rating': 4.2,
                'food_type': 'veg',
                'restaurant_type': json.dumps(['Restaurant', 'Fast Food']),
                'dietary_options': json.dumps(['Vegetarian', 'Vegan', 'Jain']),
                'mood': json.dumps(['Casual', 'Family']),
                'description': 'Traditional thali meals'
            },
            {
                'name': 'Food Street Delights',
                'cuisine': json.dumps(['Indian', 'Chinese', 'Fast Food']),
                'cost': 150,
                'rating': 4.0,
                'food_type': 'any',
                'restaurant_type': json.dumps(['Fast Food']),
                'dietary_options': json.dumps(['Vegetarian', 'Non-Vegetarian', 'Vegan']),
                'mood': json.dumps(['Casual', 'Party']),
                'description': 'Street food favorites with modern twist'
            },
            {
                'name': 'Veggie Paradise',
                'cuisine': json.dumps(['Indian', 'Italian', 'Chinese']),
                'cost': 200,
                'rating': 4.3,
                'food_type': 'veg',
                'restaurant_type': json.dumps(['Restaurant']),
                'dietary_options': json.dumps(['Vegetarian', 'Vegan', 'Jain', 'Lactose Free']),
                'mood': json.dumps(['Family', 'Casual']),
                'description': 'Purely vegetarian with diverse cuisines'
            },
            {
                'name': 'Non-Veg House',
                'cuisine': json.dumps(['Indian']),
                'cost': 250,
                'rating': 4.4,
                'food_type': 'non-veg',
                'restaurant_type': json.dumps(['Restaurant']),
                'dietary_options': json.dumps(['Non-Vegetarian']),
                'mood': json.dumps(['Family', 'Party']),
                'description': 'Specializes in meat-based curries'
            },
        ]
        
        for data in restaurants_data:
            restaurant = Restaurant(**data)
            db.session.add(restaurant)
        
        db.session.commit()

# ===================== RUN APPLICATION =====================

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
