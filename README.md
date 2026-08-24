# DineMatch – Intelligent Group Food Decision Assistant

A modern web application that helps groups make collaborative dining decisions by finding restaurants that satisfy everyone's preferences.

## 🎯 Problem Statement

When a group of people wants to eat together, everyone has different preferences—different budgets, cuisines, dietary requirements, and restaurant types. Finding a restaurant that makes everyone happy is difficult and time-consuming.

## 💡 Solution

DineMatch uses a smart matching algorithm to:
1. Collect preferences from all group members
2. Compare preferences with a restaurant database
3. Calculate a **Group Match Score** for each restaurant
4. Highlight individual member compatibility
5. Allow the group to vote and decide together

## ✨ Key Features

### 1. **Group Match Scoring (100-point scale)**
   - **Cuisine Match (30 points)**: How many members prefer the restaurant's cuisine
   - **Budget Match (25 points)**: How many members can afford it
   - **Food Type Match (20 points)**: Vegetarian/Non-veg/Vegan compatibility
   - **Restaurant Type Match (10 points)**: Café, Restaurant, Fast Food, Buffet alignment
   - **Rating (10 points)**: Higher-rated restaurants score more
   - **Mood Match (5 points)**: Casual, Party, Family, Study Break compatibility

### 2. **Individual Fairness Display**
Shows how well each group member's preferences match the recommended restaurant:
```
Sathvika   ███████████████████ 95%
Rahul      ██████████████████  90%
Priya      ███████████████████ 94%
Ananya     ████████████████    80%
```

### 3. **Simple Workflow**
- Create or join a group
- Enter individual preferences
- View group preference summary
- Get restaurant recommendations
- Vote as a group
- Calculate split bill

### 4. **Conflict Detection**
- Detects preference conflicts (e.g., Indian vs Chinese)
- Detects budget differences
- Suggests compromises

### 5. **AI-Enhanced Explanations (Optional)**
- Uses Gemini API to explain why restaurants were recommended
- Falls back to built-in explanations if API unavailable

## 🛠️ Technology Stack

**Frontend**: HTML, CSS, Bootstrap 5, JavaScript
**Backend**: Python, Flask
**Database**: SQLite
**Optional AI**: Google Gemini API

## 📊 Recommendation Algorithm

The algorithm is **intentionally simple** (no ML/DL):

```python
score = 0
score += cuisine_match_points(restaurant, preferences)  # 30
score += budget_match_points(restaurant, preferences)   # 25
score += food_type_match_points(restaurant, preferences) # 20
score += restaurant_type_match_points(restaurant, preferences) # 10
score += rating_match_points(restaurant)                # 10
score += mood_match_points(restaurant, preferences)     # 5

match_percentage = (score / 100) * 100
```

For each member's individual score:
```python
individual_score = weighted_sum_of_compatible_features
```

## 📁 Database Structure

### groups
- id, group_code, group_name, member_count, created_at

### members
- id, group_id, name, budget, cuisine, food_type, restaurant_type, dietary_requirement, mood

### restaurants
- id, name, cuisine, cost, rating, food_type, restaurant_type, dietary_options, mood, description

### votes
- id, group_id, member_id, restaurant_id

## 🚀 Installation

### Requirements
- Python 3.8+
- pip

### Steps

1. **Clone the repository**
```bash
git clone https://github.com/sathvika-2006-06/DineMatch.git
cd DineMatch
```

2. **Create virtual environment** (optional but recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables** (optional for Gemini API)
```bash
# Create .env file
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

5. **Run the application**
```bash
python app.py
```

6. **Open in browser**
```
http://127.0.0.1:5000
```

## 📖 How to Use

### Step 1: Create a Group
- Click "Create Group"
- Enter group name and number of members
- Get a unique Group ID (e.g., DM4821)

### Step 2: Join the Group
- Click "Join Group"
- Enter the Group ID
- Enter your name
- Fill in your preferences

### Step 3: View Preferences
- After all members join, see the group preference summary
- Click "Find Best Restaurants"

### Step 4: Get Recommendations
- View top 5 restaurants ranked by Group Match Score
- See your personal compatibility with each restaurant
- View reasons for recommendations

### Step 5: Vote
- Each member votes for their favorite
- See live voting results

### Step 6: Final Result
- See winning restaurant
- Calculate split bill

## 🧮 Split Bill Calculator

Simple tool to divide the total bill among group members:
- Input: Total bill amount
- Input: Number of members
- Output: Amount per person
- Optional: Add tip and recalculate

## 🔧 Project Structure

```
DineMatch/
├── app.py                    # Main Flask application
├── database.db              # SQLite database
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (optional)
├── README.md               # This file
│
├── templates/
│   ├── index.html          # Home page
│   ├── create_group.html   # Group creation
│   ├── join_group.html     # Join existing group
│   ├── preferences.html    # Preference form
│   ├── group_summary.html  # Group preferences summary
│   ├── recommendations.html # Restaurant recommendations
│   ├── voting.html         # Voting page
│   ├── result.html         # Final result
│   └── split_bill.html     # Bill splitter
│
├── static/
│   ├── style.css           # Main stylesheet
│   └── script.js           # Client-side logic
```

## 🎓 How to Explain in Viva

**Core Concept**: 
"DineMatch solves group dining by finding restaurants that maximize overall group satisfaction while considering individual fairness."

**Unique Feature**: 
"Unlike normal restaurant apps that recommend based on one person's preferences, DineMatch calculates a Group Match Score that ensures no single member is extremely unhappy."

**Algorithm Complexity**: 
"Simple, weighted scoring system - no machine learning. Easy to understand and modify."

**Real-World Scenario**:
"Imagine 4 friends: one wants Indian food with ₹200 budget, another wants Chinese with ₹500 budget, one is vegetarian, one is vegan. DineMatch finds a restaurant that serves both cuisines, accommodates both diets, and fits a middle-ground budget."

## 📚 Sample Restaurant Data

30-50 restaurants across:
- Indian, Chinese, Italian, Mexican, Fast Food, South Indian, North Indian
- Various budget ranges: ₹100-₹200, ₹200-₹300, ₹300-₹500, ₹500+
- Different food types: Veg, Non-Veg, Vegan
- Various restaurant types: Café, Restaurant, Fast Food, Buffet

## 🚫 Intentionally NOT Implemented

(To keep the project simple)
- Google Maps/Places API
- Real-time user authentication
- Payment gateways
- Docker/Kubernetes
- Machine Learning models
- Real restaurant database APIs
- Complex microservices

## 🎯 Demonstration Time

Complete demo flow: **5-10 minutes**
1. Create group (1 min)
2. 4 members join & enter preferences (2-3 min)
3. View recommendations (1 min)
4. Vote (1 min)
5. Calculate bill (1 min)

## 🔮 Future Enhancements

- User accounts with history
- Real restaurant API integration
- Advanced filters
- Google Maps integration for location
- Rating system after dining
- ML-based preference learning
- Mobile app version
- Social features

## 📝 License

This project is created as a B.Tech final year project demonstration.

## 👨‍💻 Author

Built by Sathvika for educational purposes.

---

**"One Group. Different Tastes. One Perfect Match."** 🍽️
